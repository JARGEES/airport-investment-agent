"""Unit tests for M3 — BTS query layer and agent tools."""

from unittest.mock import patch

import pandas as pd
import pytest

from backend.data.bts import (
    get_airport_segments,
    get_airport_summary,
    get_capacity_growth,
    get_top_routes,
)
from backend.agent.tool_schemas import TOOL_SCHEMAS


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def t100_df():
    return pd.DataFrame({
        "origin": ["BOS", "BOS", "BOS", "LAX", "LAX", "BOS", "BOS"],
        "dest":   ["JFK", "JFK", "ORD", "SFO", "JFK", "MIA", "MIA"],
        "year":   [2024,  2024,  2024,  2024,  2024,  2023,  2023],
        "month":  [1,     2,     1,     1,     1,     6,     7],
        "passengers":          [5000, 6000, 3000, 10000, 8000, 4000, 4500],
        "seats":               [6000, 7000, 4000, 12000, 9000, 5000, 5500],
        "departures_performed":[50,   60,   30,   100,   80,   40,   45],
        "departures_scheduled":[55,   62,   32,   105,   85,   42,   47],
        "distance":            [190,  190,  870,  340,   2475, 1260, 1260],
        "carrier":             ["AA", "AA", "UA", "DL",  "AA", "AA", "AA"],
        "freight":             [100,  120,  80,   500,   300,  90,   95],
    })


# ── BTS query layer ──────────────────────────────────────────────────

class TestGetAirportSegments:
    def test_filters_by_iata(self, t100_df):
        segs = get_airport_segments(t100_df, "BOS")
        assert len(segs) == 5
        assert (segs["origin"] == "BOS").all()

    def test_filters_by_year(self, t100_df):
        segs = get_airport_segments(t100_df, "BOS", year=2024)
        assert len(segs) == 3

    def test_case_insensitive(self, t100_df):
        segs = get_airport_segments(t100_df, "bos", year=2024)
        assert len(segs) == 3

    def test_no_match(self, t100_df):
        segs = get_airport_segments(t100_df, "ZZZ")
        assert segs.empty


class TestGetAirportSummary:
    def test_aggregates_correctly(self, t100_df):
        s = get_airport_summary(t100_df, "BOS", 2024)
        assert s["iata"] == "BOS"
        assert s["total_passengers"] == 5000 + 6000 + 3000
        assert s["total_seats"] == 6000 + 7000 + 4000
        assert s["departures_performed"] == 50 + 60 + 30
        assert s["departures_scheduled"] == 55 + 62 + 32
        assert s["segment_count"] == 3

    def test_empty_airport(self, t100_df):
        s = get_airport_summary(t100_df, "ZZZ", 2024)
        assert s["total_passengers"] == 0
        assert s["segment_count"] == 0


class TestGetTopRoutes:
    def test_returns_ranked(self, t100_df):
        routes = get_top_routes(t100_df, "BOS", 2024, n=5)
        assert len(routes) == 2
        assert routes[0]["destination"] == "JFK"
        assert routes[0]["passengers"] == 11000

    def test_empty(self, t100_df):
        routes = get_top_routes(t100_df, "ZZZ", 2024)
        assert routes == []


class TestCapacityGrowth:
    def test_positive_growth(self, t100_df):
        growth = get_capacity_growth(t100_df, "BOS", 2024, 2023)
        seats_2024 = 6000 + 7000 + 4000
        seats_2023 = 5000 + 5500
        expected = (seats_2024 - seats_2023) / seats_2023
        assert growth == pytest.approx(expected)

    def test_no_prior_data(self, t100_df):
        growth = get_capacity_growth(t100_df, "LAX", 2024, 2023)
        assert growth is None


# ── Tool schemas ──────────────────────────────────────────────────────

class TestToolSchemas:
    def test_six_tools_defined(self):
        assert len(TOOL_SCHEMAS) == 6

    def test_all_have_function_type(self):
        for schema in TOOL_SCHEMAS:
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_expected_names(self):
        names = {s["function"]["name"] for s in TOOL_SCHEMAS}
        assert names == {
            "search_airports",
            "get_airport_stats",
            "compare_airports",
            "score_airports",
            "get_flight_breakdown",
            "get_demand_analysis",
        }

    def test_required_params(self):
        by_name = {s["function"]["name"]: s["function"] for s in TOOL_SCHEMAS}
        assert "iata_code" in by_name["get_airport_stats"]["parameters"]["properties"]
        assert "codes" in by_name["compare_airports"]["parameters"]["properties"]
        assert "codes" in by_name["score_airports"]["parameters"]["properties"]


# ── Agent tools (with mocked data) ───────────────────────────────────

class TestSearchAirportsTool:
    def test_returns_list(self):
        from backend.agent.tools import search_airports
        results = search_airports(region="New England")
        assert len(results) > 0
        assert results[0]["state"] in ["CT", "ME", "MA", "NH", "RI", "VT"]

    def test_filter_by_state(self):
        from backend.agent.tools import search_airports
        results = search_airports(state="CA")
        assert all(r["state"] == "CA" for r in results)

    def test_min_passengers(self):
        from backend.agent.tools import search_airports
        results = search_airports(min_passengers=50_000_000)
        assert all(r["estimated_annual_pax"] >= 50_000_000 for r in results)

    def test_result_shape(self):
        from backend.agent.tools import search_airports
        results = search_airports(state="NY")
        if results:
            r = results[0]
            assert "iata" in r
            assert "name" in r
            assert "city" in r
            assert "hub_size" in r
            assert "runways" in r


class TestToolsWithMockedT100:
    """Tests that exercise the six agent tools with a synthetic T-100 DataFrame."""

    @pytest.fixture(autouse=True)
    def mock_data(self, t100_df):
        with patch("backend.agent.tools.load_t100_data", return_value=t100_df), \
             patch("backend.data.bts.load_ontime_data", return_value=None), \
             patch("backend.agent.tools.get_data_vintage", return_value={
                 "source": "test", "latest_period": "2024-02", "years_covered": [2023, 2024], "record_count": 7
             }):
            yield

    def test_get_airport_stats(self):
        from backend.agent.tools import get_airport_stats
        stats = get_airport_stats("BOS", year=2024)
        assert stats["iata"] == "BOS"
        assert stats["total_passengers"] == 14000
        assert stats["metrics"]["load_factor"] is not None
        assert stats["data_vintage"] == "2024-02"
        assert len(stats["top_routes"]) > 0

    def test_compare_airports(self):
        from backend.agent.tools import compare_airports
        result = compare_airports(["BOS", "LAX"], metrics=["load_factor"])
        assert len(result["airports"]) == 2
        assert "load_factor" in result["rankings"]
        assert result["year"] == 2024

    def test_score_airports(self):
        from backend.agent.tools import score_airports
        result = score_airports(["BOS", "LAX"])
        assert len(result["ranked"]) == 2
        assert result["ranked"][0]["ios_total"] >= result["ranked"][1]["ios_total"]
        assert "weights_used" in result

    def test_get_flight_breakdown(self):
        from backend.agent.tools import get_flight_breakdown
        fb = get_flight_breakdown("BOS", year=2024)
        assert fb["iata"] == "BOS"
        assert fb["total_flights"] == 140
        bd = fb["distance_breakdown"]
        assert bd["short_haul"] + bd["medium_haul"] + bd["long_haul"] == 140
        assert len(fb["top_carriers"]) > 0

    def test_get_demand_analysis(self):
        from backend.agent.tools import get_demand_analysis
        da = get_demand_analysis("BOS")
        assert da["iata"] == "BOS"
        assert len(da["capacity_trend"]) > 0
        assert da["assessment"]
        assert "data_vintage" in da
