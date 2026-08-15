from __future__ import annotations

from typing import Optional

import pandas as pd


def calc_load_factor(passengers: int, seats: int) -> Optional[float]:
    if seats <= 0:
        return None
    return passengers / seats


def calc_utilization(departures_performed: int, departures_scheduled: int) -> Optional[float]:
    if departures_scheduled <= 0:
        return None
    return departures_performed / departures_scheduled


def calc_pax_growth(pax_current: int, pax_prior: int) -> Optional[float]:
    if pax_prior <= 0:
        return None
    return (pax_current - pax_prior) / pax_prior


def calc_congestion_index(
    delay_data: Optional[dict] = None,
    utilization: Optional[float] = None,
    load_factor: Optional[float] = None,
) -> Optional[float]:
    """Congestion from on-time delay data when available, otherwise from
    utilization and load factor as a proxy.

    delay_data keys: pct_delayed (0-1 fraction of flights delayed),
                     avg_delay_minutes (average delay in minutes).
    """
    if delay_data and "pct_delayed" in delay_data and "avg_delay_minutes" in delay_data:
        pct = delay_data["pct_delayed"]
        avg = delay_data["avg_delay_minutes"]
        if avg < 0:
            avg = 0.0
        raw = pct * 0.6 + min(avg / 60.0, 1.0) * 0.4
        return min(max(raw, 0.0), 1.0)

    if utilization is not None and load_factor is not None:
        proxy = utilization * 0.6 + load_factor * 0.4
        return min(max(proxy * 0.8, 0.0), 1.0)

    return None


def calc_long_haul_ratio(segments_df: pd.DataFrame) -> Optional[float]:
    """Fraction of flights that are long-haul (distance > 1500 mi)."""
    if segments_df.empty or "distance" not in segments_df.columns:
        return None

    dep_col = "departures_performed" if "departures_performed" in segments_df.columns else None
    if dep_col is None:
        return None

    total = segments_df[dep_col].sum()
    if total <= 0:
        return None

    long_haul = segments_df.loc[segments_df["distance"] > 1500, dep_col].sum()
    return long_haul / total


def calc_unmet_demand(
    airport_capacity_growth: float,
    msa_pop_growth: float,
) -> float:
    """Positive gap = population growing faster than airport capacity."""
    return msa_pop_growth - airport_capacity_growth
