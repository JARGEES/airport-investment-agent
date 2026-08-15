from __future__ import annotations

from typing import Optional

METRIC_KEYS = [
    "load_factor",
    "utilization",
    "pax_growth",
    "congestion",
    "long_haul_ratio",
    "unmet_demand",
]


def normalize(value: float, min_val: float, max_val: float) -> float:
    if max_val == min_val:
        return 0.5
    raw = (value - min_val) / (max_val - min_val)
    return min(max(raw, 0.0), 1.0)


def compute_dataset_bounds(
    airport_metrics: list[dict],
) -> dict[str, tuple[float, float]]:
    """Compute min/max for each KPI across all airports.

    airport_metrics: list of dicts, each with optional keys matching METRIC_KEYS.
    Returns {metric_key: (min_val, max_val)}.
    """
    bounds: dict[str, tuple[float, float]] = {}

    for key in METRIC_KEYS:
        values = [
            m[key] for m in airport_metrics if m.get(key) is not None
        ]
        if values:
            bounds[key] = (min(values), max(values))
        else:
            bounds[key] = (0.0, 1.0)

    return bounds


def normalize_metrics(
    raw: dict[str, Optional[float]],
    bounds: dict[str, tuple[float, float]],
) -> dict[str, Optional[float]]:
    """Normalize a single airport's raw metrics using precomputed bounds."""
    result: dict[str, Optional[float]] = {}
    for key in METRIC_KEYS:
        val = raw.get(key)
        if val is None:
            result[key] = None
            continue
        min_val, max_val = bounds.get(key, (0.0, 1.0))
        result[key] = normalize(val, min_val, max_val)
    return result
