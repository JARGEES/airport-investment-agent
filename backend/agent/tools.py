from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.data.airports import (
    Airport,
    get_airport,
    get_all_airports,
    search_airports as _search_airports_data,
)
from backend.data.bts import (
    get_airport_segments,
    get_airport_summary,
    get_capacity_growth,
    get_delay_stats,
    get_top_routes,
)
from backend.data.census import get_airport_msa_growth
from backend.data.loader import get_data_vintage, load_t100_data
from backend.scoring.engine import ScoredAirport, compute_ios, rank_airports
from backend.scoring.metrics import (
    calc_congestion_index,
    calc_load_factor,
    calc_long_haul_ratio,
    calc_pax_growth,
    calc_unmet_demand,
    calc_utilization,
)
from backend.config import DEFAULT_WEIGHTS
from backend.scoring.normalizer import METRIC_KEYS, compute_dataset_bounds


def _get_latest_year(df: pd.DataFrame) -> int:
    if "year" in df.columns:
        return int(df["year"].max())
    return 2024


def _resolve_year(df: pd.DataFrame, year: Optional[int]) -> int:
    return year if year is not None else _get_latest_year(df)


def _vintage_string() -> str:
    v = get_data_vintage()
    return v.get("latest_period", "unknown")


def _compute_airport_metrics(
    df: pd.DataFrame,
    iata: str,
    year: int,
) -> dict[str, Optional[float]]:
    summary = get_airport_summary(df, iata, year)
    segs = get_airport_segments(df, iata, year)

    lf = calc_load_factor(summary["total_passengers"], summary["total_seats"])
    util = calc_utilization(summary["departures_performed"], summary["departures_scheduled"])

    prior_summary = get_airport_summary(df, iata, year - 1)
    growth = calc_pax_growth(summary["total_passengers"], prior_summary["total_passengers"])

    delay = get_delay_stats(iata, year)
    congestion = calc_congestion_index(
        delay_data=delay,
        utilization=util,
        load_factor=lf,
    )

    lh_ratio = calc_long_haul_ratio(segs)

    cap_growth = get_capacity_growth(df, iata, year, year - 1)
    msa = get_airport_msa_growth(iata)
    if cap_growth is not None and msa is not None:
        unmet = calc_unmet_demand(cap_growth, msa["cagr"])
    else:
        unmet = None

    return {
        "load_factor": lf,
        "utilization": util,
        "pax_growth": growth,
        "congestion": congestion,
        "long_haul_ratio": lh_ratio,
        "unmet_demand": unmet,
    }


def _get_dataset_bounds(df: pd.DataFrame, year: int) -> dict[str, tuple[float, float]]:
    airports = get_all_airports(respect_mode=True)
    all_metrics = []
    for ap in airports:
        m = _compute_airport_metrics(df, ap.iata, year)
        all_metrics.append(m)
    return compute_dataset_bounds(all_metrics)


# ── Tool 1: search_airports ──────────────────────────────────────────

def search_airports(
    region: Optional[str] = None,
    state: Optional[str] = None,
    min_passengers: Optional[int] = None,
    airport_type: Optional[str] = None,
) -> list[dict]:
    results = _search_airports_data(
        region=region,
        state=state,
        min_passengers=min_passengers,
        hub_size=airport_type,
    )
    return [
        {
            "iata": a.iata,
            "name": a.name,
            "city": a.city,
            "state": a.state,
            "hub_size": a.hub_size,
            "runways": a.runways,
            "estimated_annual_pax": a.estimated_annual_pax,
        }
        for a in results
    ]


# ── Tool 2: get_airport_stats ────────────────────────────────────────

def get_airport_stats(iata_code: str, year: Optional[int] = None) -> dict:
    df = load_t100_data()
    yr = _resolve_year(df, year)
    summary = get_airport_summary(df, iata_code, yr)
    metrics = _compute_airport_metrics(df, iata_code, yr)
    top = get_top_routes(df, iata_code, yr, n=10)

    airport = get_airport(iata_code)
    name = airport.name if airport else iata_code.upper()

    return {
        "iata": iata_code.upper(),
        "name": name,
        "year": yr,
        "total_passengers": summary["total_passengers"],
        "total_seats": summary["total_seats"],
        "departures_performed": summary["departures_performed"],
        "departures_scheduled": summary["departures_scheduled"],
        "total_freight": summary["total_freight"],
        "metrics": {
            k: round(v, 4) if v is not None else None
            for k, v in metrics.items()
        },
        "top_routes": top,
        "data_vintage": _vintage_string(),
    }


# ── Tool 3: compare_airports ─────────────────────────────────────────

def compare_airports(
    codes: list[str],
    metrics: Optional[list[str]] = None,
) -> dict:
    df = load_t100_data()
    yr = _get_latest_year(df)

    results = []
    for code in codes:
        stats = get_airport_stats(code, yr)
        if metrics:
            filtered_metrics = {
                k: v for k, v in stats["metrics"].items() if k in metrics
            }
        else:
            filtered_metrics = stats["metrics"]

        results.append({
            "iata": stats["iata"],
            "name": stats["name"],
            "year": yr,
            "total_passengers": stats["total_passengers"],
            "metrics": filtered_metrics,
        })

    metric_keys = metrics or list(METRIC_KEYS)
    rankings: dict[str, list[dict]] = {}
    for key in metric_keys:
        vals = [
            (r["iata"], r["metrics"].get(key))
            for r in results
            if r["metrics"].get(key) is not None
        ]
        vals.sort(key=lambda x: x[1], reverse=True)
        rankings[key] = [{"iata": v[0], "value": v[1], "rank": i + 1} for i, v in enumerate(vals)]

    return {
        "airports": results,
        "rankings": rankings,
        "year": yr,
        "data_vintage": _vintage_string(),
    }


# ── Tool 4: score_airports ───────────────────────────────────────────

def score_airports(
    codes: list[str],
    weights: Optional[dict[str, float]] = None,
) -> dict:
    df = load_t100_data()
    yr = _get_latest_year(df)
    bounds = _get_dataset_bounds(df, yr)

    airport_dicts = []
    for code in codes:
        ap = get_airport(code)
        name = ap.name if ap else code.upper()
        m = _compute_airport_metrics(df, code, yr)
        airport_dicts.append({"iata": code.upper(), "name": name, **m})

    ranked = rank_airports(airport_dicts, bounds, weights=weights, data_vintage=_vintage_string())

    return {
        "ranked": [s.to_dict() for s in ranked],
        "weights_used": weights or dict(DEFAULT_WEIGHTS),
        "year": yr,
        "data_vintage": _vintage_string(),
    }


# ── Tool 5: get_flight_breakdown ─────────────────────────────────────

def get_flight_breakdown(iata_code: str, year: Optional[int] = None) -> dict:
    df = load_t100_data()
    yr = _resolve_year(df, year)
    segs = get_airport_segments(df, iata_code, yr)

    airport = get_airport(iata_code)
    name = airport.name if airport else iata_code.upper()

    dep_col = "departures_performed" if "departures_performed" in segs.columns else None
    total_flights = int(segs[dep_col].sum()) if dep_col and not segs.empty else 0

    breakdown = {"short_haul": 0, "medium_haul": 0, "long_haul": 0}
    if not segs.empty and "distance" in segs.columns and dep_col:
        short = segs.loc[segs["distance"] <= 500, dep_col].sum()
        medium = segs.loc[(segs["distance"] > 500) & (segs["distance"] <= 1500), dep_col].sum()
        long = segs.loc[segs["distance"] > 1500, dep_col].sum()
        breakdown = {
            "short_haul": int(short),
            "medium_haul": int(medium),
            "long_haul": int(long),
        }

    pct = {}
    if total_flights > 0:
        pct = {k: round(v / total_flights, 4) for k, v in breakdown.items()}

    carriers: list[dict] = []
    if not segs.empty and "carrier" in segs.columns and dep_col:
        carrier_agg = (
            segs.groupby("carrier")[dep_col]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        carriers = [
            {"carrier": c, "flights": int(f)}
            for c, f in carrier_agg.items()
        ]

    top_dest = get_top_routes(df, iata_code, yr, n=10)

    return {
        "iata": iata_code.upper(),
        "name": name,
        "year": yr,
        "total_flights": total_flights,
        "distance_breakdown": breakdown,
        "distance_percentages": pct,
        "top_carriers": carriers,
        "top_destinations": top_dest,
        "data_vintage": _vintage_string(),
    }


# ── Tool 6: get_demand_analysis ──────────────────────────────────────

def get_demand_analysis(iata_code: str) -> dict:
    df = load_t100_data()
    airport = get_airport(iata_code)
    name = airport.name if airport else iata_code.upper()

    years = sorted(df["year"].unique()) if "year" in df.columns else []
    years = [int(y) for y in years]

    capacity_trend: list[dict] = []
    for y in years:
        s = get_airport_summary(df, iata_code, y)
        capacity_trend.append({
            "year": y,
            "passengers": s["total_passengers"],
            "seats": s["total_seats"],
            "departures": s["departures_performed"],
        })

    cap_growth = None
    if len(years) >= 2:
        cap_growth = get_capacity_growth(df, iata_code, years[-1], years[-2])

    msa = get_airport_msa_growth(iata_code)
    msa_growth_rate = msa["cagr"] if msa else None

    unmet = None
    if cap_growth is not None and msa_growth_rate is not None:
        unmet = calc_unmet_demand(cap_growth, msa_growth_rate)

    if unmet is not None:
        if unmet > 0.01:
            assessment = "High unmet demand — regional population growing significantly faster than airport capacity"
        elif unmet > 0:
            assessment = "Moderate unmet demand — population growth slightly outpacing capacity"
        elif unmet > -0.01:
            assessment = "Balanced — capacity growth roughly matching population growth"
        else:
            assessment = "Overcapacity risk — airport capacity growing faster than regional demand"
    else:
        assessment = "Insufficient data to assess demand gap"

    saturation_indicators: list[str] = []
    if len(years) >= 1:
        latest_yr = years[-1]
        metrics = _compute_airport_metrics(df, iata_code, latest_yr)
        if metrics.get("load_factor") is not None and metrics["load_factor"] > 0.85:
            saturation_indicators.append(f"High load factor ({metrics['load_factor']:.1%}) — seats nearly full")
        if metrics.get("utilization") is not None and metrics["utilization"] > 0.95:
            saturation_indicators.append(f"High utilization ({metrics['utilization']:.1%}) — near physical capacity")
        if metrics.get("congestion") is not None and metrics["congestion"] > 0.6:
            saturation_indicators.append(f"Elevated congestion ({metrics['congestion']:.2f}) — operational bottleneck")

    return {
        "iata": iata_code.upper(),
        "name": name,
        "capacity_trend": capacity_trend,
        "capacity_growth_yoy": round(cap_growth, 4) if cap_growth is not None else None,
        "msa_info": {
            "msa_name": msa["msa_name"] if msa else None,
            "latest_population": msa["latest_population"] if msa else None,
            "population_cagr": msa["cagr"] if msa else None,
        },
        "unmet_demand": round(unmet, 4) if unmet is not None else None,
        "assessment": assessment,
        "saturation_indicators": saturation_indicators,
        "data_vintage": _vintage_string(),
    }
