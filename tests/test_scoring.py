"""Unit tests for the scoring engine — metrics, normalizer, and IOS computation."""

import pandas as pd
import pytest

from backend.scoring.metrics import (
    calc_congestion_index,
    calc_load_factor,
    calc_long_haul_ratio,
    calc_pax_growth,
    calc_unmet_demand,
    calc_utilization,
)
from backend.scoring.normalizer import (
    compute_dataset_bounds,
    normalize,
    normalize_metrics,
)
from backend.scoring.engine import (
    ScoredAirport,
    compute_ios,
    rank_airports,
)


# ── Metrics ──────────────────────────────────────────────────────────

class TestLoadFactor:
    def test_normal(self):
        assert calc_load_factor(800, 1000) == pytest.approx(0.8)

    def test_full(self):
        assert calc_load_factor(1000, 1000) == pytest.approx(1.0)

    def test_zero_seats(self):
        assert calc_load_factor(100, 0) is None

    def test_negative_seats(self):
        assert calc_load_factor(100, -5) is None


class TestUtilization:
    def test_normal(self):
        assert calc_utilization(90, 100) == pytest.approx(0.9)

    def test_perfect(self):
        assert calc_utilization(100, 100) == pytest.approx(1.0)

    def test_zero_scheduled(self):
        assert calc_utilization(10, 0) is None


class TestPaxGrowth:
    def test_positive(self):
        assert calc_pax_growth(1100, 1000) == pytest.approx(0.1)

    def test_negative(self):
        assert calc_pax_growth(900, 1000) == pytest.approx(-0.1)

    def test_zero_prior(self):
        assert calc_pax_growth(100, 0) is None

    def test_no_change(self):
        assert calc_pax_growth(1000, 1000) == pytest.approx(0.0)


class TestCongestionIndex:
    def test_from_delay_data(self):
        result = calc_congestion_index(
            delay_data={"pct_delayed": 0.4, "avg_delay_minutes": 30}
        )
        assert result is not None
        expected = 0.4 * 0.6 + (30 / 60) * 0.4
        assert result == pytest.approx(expected)

    def test_from_proxy(self):
        result = calc_congestion_index(utilization=0.9, load_factor=0.85)
        assert result is not None
        proxy = (0.9 * 0.6 + 0.85 * 0.4) * 0.8
        assert result == pytest.approx(proxy)

    def test_no_data(self):
        assert calc_congestion_index() is None

    def test_clamped_to_1(self):
        result = calc_congestion_index(
            delay_data={"pct_delayed": 1.0, "avg_delay_minutes": 120}
        )
        assert result <= 1.0

    def test_negative_delay_treated_as_zero(self):
        result = calc_congestion_index(
            delay_data={"pct_delayed": 0.5, "avg_delay_minutes": -10}
        )
        expected = 0.5 * 0.6 + 0.0 * 0.4
        assert result == pytest.approx(expected)


class TestLongHaulRatio:
    def test_normal(self):
        df = pd.DataFrame({
            "distance": [500, 800, 1600, 2000, 3000],
            "departures_performed": [10, 10, 10, 10, 10],
        })
        assert calc_long_haul_ratio(df) == pytest.approx(0.6)

    def test_no_long_haul(self):
        df = pd.DataFrame({
            "distance": [200, 500, 1000],
            "departures_performed": [10, 10, 10],
        })
        assert calc_long_haul_ratio(df) == pytest.approx(0.0)

    def test_empty_df(self):
        assert calc_long_haul_ratio(pd.DataFrame()) is None

    def test_missing_columns(self):
        df = pd.DataFrame({"foo": [1, 2]})
        assert calc_long_haul_ratio(df) is None


class TestUnmetDemand:
    def test_positive_gap(self):
        assert calc_unmet_demand(0.02, 0.05) == pytest.approx(0.03)

    def test_negative_gap(self):
        assert calc_unmet_demand(0.05, 0.02) == pytest.approx(-0.03)

    def test_no_gap(self):
        assert calc_unmet_demand(0.03, 0.03) == pytest.approx(0.0)


# ── Normalizer ───────────────────────────────────────────────────────

class TestNormalize:
    def test_midpoint(self):
        assert normalize(50, 0, 100) == pytest.approx(0.5)

    def test_at_min(self):
        assert normalize(0, 0, 100) == pytest.approx(0.0)

    def test_at_max(self):
        assert normalize(100, 0, 100) == pytest.approx(1.0)

    def test_equal_bounds(self):
        assert normalize(5, 5, 5) == pytest.approx(0.5)

    def test_clamped_above(self):
        assert normalize(150, 0, 100) == pytest.approx(1.0)

    def test_clamped_below(self):
        assert normalize(-10, 0, 100) == pytest.approx(0.0)


class TestComputeDatasetBounds:
    def test_basic(self):
        metrics = [
            {"load_factor": 0.7, "utilization": 0.8, "pax_growth": 0.05},
            {"load_factor": 0.9, "utilization": 0.6, "pax_growth": 0.10},
        ]
        bounds = compute_dataset_bounds(metrics)
        assert bounds["load_factor"] == (0.7, 0.9)
        assert bounds["utilization"] == (0.6, 0.8)
        assert bounds["pax_growth"] == (0.05, 0.10)

    def test_missing_key_defaults(self):
        metrics = [{"load_factor": 0.8}]
        bounds = compute_dataset_bounds(metrics)
        assert bounds["congestion"] == (0.0, 1.0)

    def test_empty_list(self):
        bounds = compute_dataset_bounds([])
        for key in bounds:
            assert bounds[key] == (0.0, 1.0)


class TestNormalizeMetrics:
    def test_full_set(self):
        raw = {
            "load_factor": 0.85,
            "utilization": 0.90,
            "pax_growth": 0.08,
            "congestion": 0.5,
            "long_haul_ratio": 0.3,
            "unmet_demand": 0.02,
        }
        bounds = {
            "load_factor": (0.5, 1.0),
            "utilization": (0.5, 1.0),
            "pax_growth": (0.0, 0.15),
            "congestion": (0.0, 1.0),
            "long_haul_ratio": (0.0, 0.6),
            "unmet_demand": (-0.05, 0.05),
        }
        result = normalize_metrics(raw, bounds)
        assert result["load_factor"] == pytest.approx(0.7)
        assert result["pax_growth"] == pytest.approx(0.08 / 0.15, abs=1e-4)

    def test_none_passthrough(self):
        raw = {"load_factor": 0.8, "congestion": None}
        bounds = {"load_factor": (0.5, 1.0), "congestion": (0.0, 1.0)}
        result = normalize_metrics(raw, bounds)
        assert result["congestion"] is None


# ── IOS Engine ───────────────────────────────────────────────────────

class TestComputeIOS:
    def test_all_components_present(self):
        metrics = {
            "load_factor": 0.85,
            "utilization": 0.90,
            "pax_growth": 0.08,
            "congestion": 0.5,
            "long_haul_ratio": 0.3,
            "unmet_demand": 0.02,
        }
        bounds = {k: (0.0, 1.0) for k in metrics}
        result = compute_ios(metrics, bounds, iata="TST", name="Test Airport")
        assert 0 <= result.ios_total <= 100
        assert result.confidence == "high"
        assert result.available_components == 6

    def test_partial_data_medium_confidence(self):
        metrics = {
            "load_factor": 0.85,
            "utilization": 0.90,
            "pax_growth": 0.08,
            "congestion": 0.5,
        }
        bounds = {k: (0.0, 1.0) for k in metrics}
        result = compute_ios(metrics, bounds)
        assert result.confidence == "medium"
        assert result.available_components == 4

    def test_low_confidence(self):
        metrics = {"load_factor": 0.85, "utilization": 0.90}
        bounds = {k: (0.0, 1.0) for k in metrics}
        result = compute_ios(metrics, bounds)
        assert result.confidence == "low"

    def test_rescales_for_missing(self):
        """With only one component at max, IOS should be 100 (rescaled)."""
        metrics = {"load_factor": 1.0}
        bounds = {"load_factor": (0.0, 1.0)}
        result = compute_ios(metrics, bounds)
        assert result.ios_total == pytest.approx(100.0)

    def test_custom_weights(self):
        metrics = {
            "load_factor": 1.0,
            "utilization": 0.0,
        }
        bounds = {k: (0.0, 1.0) for k in metrics}
        w = {"load_factor": 0.8, "utilization": 0.2}
        result = compute_ios(metrics, bounds, weights=w)
        assert result.ios_total == pytest.approx(80.0)

    def test_to_dict(self):
        metrics = {"load_factor": 0.85}
        bounds = {"load_factor": (0.0, 1.0)}
        result = compute_ios(metrics, bounds, iata="BOS", name="Boston Logan")
        d = result.to_dict()
        assert d["iata"] == "BOS"
        assert isinstance(d["ios_total"], float)
        assert d["confidence"] in ("high", "medium", "low")


class TestRankAirports:
    def test_ranking_order(self):
        airports = [
            {"iata": "LOW", "name": "Low Airport", "load_factor": 0.3, "utilization": 0.4},
            {"iata": "HIGH", "name": "High Airport", "load_factor": 0.9, "utilization": 0.95},
            {"iata": "MID", "name": "Mid Airport", "load_factor": 0.6, "utilization": 0.7},
        ]
        bounds = {"load_factor": (0.0, 1.0), "utilization": (0.0, 1.0)}
        ranked = rank_airports(airports, bounds)
        assert ranked[0].iata == "HIGH"
        assert ranked[-1].iata == "LOW"

    def test_empty_list(self):
        assert rank_airports([], {}) == []
