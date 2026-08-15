from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.data.loader import load_t100_data, load_ontime_data


def get_airport_segments(
    df: pd.DataFrame,
    iata: str,
    year: Optional[int] = None,
) -> pd.DataFrame:
    mask = df["origin"] == iata.upper()
    if year is not None and "year" in df.columns:
        mask &= df["year"] == year
    return df.loc[mask].copy()


def get_airport_summary(
    df: pd.DataFrame,
    iata: str,
    year: Optional[int] = None,
) -> dict:
    segs = get_airport_segments(df, iata, year)
    if segs.empty:
        return {
            "iata": iata.upper(),
            "year": year,
            "total_passengers": 0,
            "total_seats": 0,
            "departures_performed": 0,
            "departures_scheduled": 0,
            "total_freight": 0,
            "segment_count": 0,
        }

    return {
        "iata": iata.upper(),
        "year": year,
        "total_passengers": int(segs["passengers"].sum()) if "passengers" in segs.columns else 0,
        "total_seats": int(segs["seats"].sum()) if "seats" in segs.columns else 0,
        "departures_performed": int(segs["departures_performed"].sum()) if "departures_performed" in segs.columns else 0,
        "departures_scheduled": int(segs["departures_scheduled"].sum()) if "departures_scheduled" in segs.columns else 0,
        "total_freight": int(segs["freight"].sum()) if "freight" in segs.columns else 0,
        "segment_count": len(segs),
    }


def get_top_routes(
    df: pd.DataFrame,
    iata: str,
    year: Optional[int] = None,
    n: int = 10,
) -> list[dict]:
    segs = get_airport_segments(df, iata, year)
    if segs.empty or "dest" not in segs.columns or "passengers" not in segs.columns:
        return []

    grouped = (
        segs.groupby("dest")
        .agg(
            passengers=("passengers", "sum"),
            flights=("departures_performed", "sum") if "departures_performed" in segs.columns else ("passengers", "count"),
        )
        .sort_values("passengers", ascending=False)
        .head(n)
    )

    return [
        {"destination": dest, "passengers": int(row["passengers"]), "flights": int(row["flights"])}
        for dest, row in grouped.iterrows()
    ]


def get_delay_stats(
    iata: str,
    year: Optional[int] = None,
) -> Optional[dict]:
    ontime = load_ontime_data()
    if ontime is None:
        return None

    col_map = {}
    for col in ontime.columns:
        lower = col.lower().strip()
        if lower in ("origin", "origin_airport_id"):
            col_map["origin"] = col
        elif lower in ("arr_delay", "arrdelay", "arrival_delay"):
            col_map["arr_delay"] = col
        elif lower in ("dep_delay", "depdelay", "departure_delay"):
            col_map["dep_delay"] = col
        elif lower == "year":
            col_map["year"] = col

    if "origin" not in col_map:
        return None

    mask = ontime[col_map["origin"]] == iata.upper()
    if year is not None and "year" in col_map:
        mask &= ontime[col_map["year"]] == year
    subset = ontime.loc[mask]

    if subset.empty:
        return None

    delay_col = col_map.get("dep_delay") or col_map.get("arr_delay")
    if delay_col is None:
        return None

    delays = pd.to_numeric(subset[delay_col], errors="coerce").dropna()
    if delays.empty:
        return None

    total = len(delays)
    delayed = (delays > 15).sum()

    return {
        "total_flights": total,
        "delayed_flights": int(delayed),
        "pct_delayed": round(delayed / total, 4) if total > 0 else 0.0,
        "avg_delay_minutes": round(float(delays.mean()), 2),
        "median_delay_minutes": round(float(delays.median()), 2),
    }


def get_capacity_growth(
    df: pd.DataFrame,
    iata: str,
    year_current: int,
    year_prior: int,
) -> Optional[float]:
    current = get_airport_summary(df, iata, year_current)
    prior = get_airport_summary(df, iata, year_prior)

    seats_curr = current["total_seats"]
    seats_prior = prior["total_seats"]

    if seats_prior <= 0:
        return None

    return (seats_curr - seats_prior) / seats_prior
