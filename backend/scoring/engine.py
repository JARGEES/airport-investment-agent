from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from backend.config import DEFAULT_WEIGHTS
from backend.scoring.normalizer import METRIC_KEYS, normalize_metrics


@dataclass
class ScoredAirport:
    iata: str
    name: str
    ios_total: float
    component_scores: dict[str, Optional[float]]
    raw_metrics: dict[str, Optional[float]]
    confidence: Literal["high", "medium", "low"]
    data_vintage: str
    available_components: int = 0

    def to_dict(self) -> dict:
        return {
            "iata": self.iata,
            "name": self.name,
            "ios_total": round(self.ios_total, 2),
            "component_scores": {
                k: round(v, 4) if v is not None else None
                for k, v in self.component_scores.items()
            },
            "raw_metrics": {
                k: round(v, 4) if v is not None else None
                for k, v in self.raw_metrics.items()
            },
            "confidence": self.confidence,
            "data_vintage": self.data_vintage,
            "available_components": self.available_components,
        }


def _confidence_level(available: int) -> Literal["high", "medium", "low"]:
    if available >= 6:
        return "high"
    if available >= 4:
        return "medium"
    return "low"


def compute_ios(
    airport_metrics: dict[str, Optional[float]],
    bounds: dict[str, tuple[float, float]],
    weights: Optional[dict[str, float]] = None,
    iata: str = "",
    name: str = "",
    data_vintage: str = "unknown",
) -> ScoredAirport:
    w = weights or DEFAULT_WEIGHTS
    normalized = normalize_metrics(airport_metrics, bounds)

    total = 0.0
    weight_sum = 0.0
    available = 0

    for key in METRIC_KEYS:
        norm_val = normalized.get(key)
        if norm_val is None:
            continue
        available += 1
        wk = w.get(key, 0.0)
        total += wk * norm_val
        weight_sum += wk

    # Re-scale to 0-100, adjusted for missing components
    if weight_sum > 0:
        ios = (total / weight_sum) * 100.0
    else:
        ios = 0.0

    return ScoredAirport(
        iata=iata,
        name=name,
        ios_total=ios,
        component_scores=normalized,
        raw_metrics=airport_metrics,
        confidence=_confidence_level(available),
        data_vintage=data_vintage,
        available_components=available,
    )


def rank_airports(
    airports: list[dict],
    bounds: dict[str, tuple[float, float]],
    weights: Optional[dict[str, float]] = None,
    data_vintage: str = "unknown",
) -> list[ScoredAirport]:
    """Score and rank a list of airports.

    Each dict in airports must have: iata, name, and metric keys from METRIC_KEYS.
    """
    scored = []
    for ap in airports:
        metrics = {k: ap.get(k) for k in METRIC_KEYS}
        scored.append(
            compute_ios(
                airport_metrics=metrics,
                bounds=bounds,
                weights=weights,
                iata=ap.get("iata", ""),
                name=ap.get("name", ""),
                data_vintage=data_vintage,
            )
        )
    scored.sort(key=lambda s: s.ios_total, reverse=True)
    return scored
