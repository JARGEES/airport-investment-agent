from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from backend.config import PROCESSED_DIR, RAW_DIR

_t100_cache: Optional[pd.DataFrame] = None
_ontime_cache: Optional[pd.DataFrame] = None


def load_t100_data() -> pd.DataFrame:
    global _t100_cache
    if _t100_cache is not None:
        return _t100_cache

    parquet_files = sorted(PROCESSED_DIR.glob("t100_*.parquet"))
    if parquet_files:
        try:
            frames = [pd.read_parquet(f) for f in parquet_files]
            _t100_cache = pd.concat(frames, ignore_index=True)
            return _t100_cache
        except ImportError:
            pass

    csv_files = sorted(RAW_DIR.glob("t100_*.csv"))
    if csv_files:
        frames = [pd.read_csv(f, low_memory=False) for f in csv_files]
        _t100_cache = pd.concat(frames, ignore_index=True)
        _normalize_t100_columns(_t100_cache)
        return _t100_cache

    raise FileNotFoundError(
        "No T-100 data found. Run data/scripts/download_bts.py first."
    )


def _normalize_t100_columns(df: pd.DataFrame) -> None:
    rename_map = {}
    for col in df.columns:
        lower = col.lower().strip()
        if lower in ("origin", "origin_airport_id", "origin_airport_code"):
            rename_map[col] = "origin"
        elif lower in ("dest", "dest_airport_id"):
            rename_map[col] = "dest"
        elif lower in ("passengers", "domestic_passengers"):
            rename_map[col] = "passengers"
        elif lower in ("seats", "available_seats", "domestic_seats"):
            rename_map[col] = "seats"
        elif lower in ("departures_performed", "dept_performed", "domestic_departures"):
            rename_map[col] = "departures_performed"
        elif lower in ("departures_scheduled", "dept_scheduled"):
            rename_map[col] = "departures_scheduled"
        elif lower in ("distance", "domestic_distance_flight"):
            rename_map[col] = "distance"
        elif lower == "year":
            rename_map[col] = "year"
        elif lower == "month":
            rename_map[col] = "month"
        elif lower in ("unique_carrier", "carrier", "unique_carrier_name"):
            rename_map[col] = "carrier"
        elif lower in ("freight", "domestic_freight_lbs"):
            rename_map[col] = "freight"

    if rename_map:
        df.rename(columns=rename_map, inplace=True)

    if "departures_performed" in df.columns and "departures_scheduled" not in df.columns:
        df["departures_scheduled"] = df["departures_performed"]

    if "reporting_month" in df.columns and "month" not in df.columns:
        df["month"] = pd.to_datetime(df["reporting_month"], errors="coerce").dt.month

    numeric_cols = ["passengers", "seats", "departures_performed", "departures_scheduled",
                    "freight", "year", "month"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "distance" in df.columns:
        df["distance"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0.0)


def load_ontime_data() -> Optional[pd.DataFrame]:
    global _ontime_cache
    if _ontime_cache is not None:
        return _ontime_cache

    parquet_files = sorted(PROCESSED_DIR.glob("ontime_*.parquet"))
    if parquet_files:
        try:
            frames = [pd.read_parquet(f) for f in parquet_files]
            _ontime_cache = pd.concat(frames, ignore_index=True)
            return _ontime_cache
        except ImportError:
            pass

    csv_files = sorted(RAW_DIR.glob("ontime_*.csv"))
    if csv_files:
        frames = [pd.read_csv(f, low_memory=False) for f in csv_files]
        _ontime_cache = pd.concat(frames, ignore_index=True)
        return _ontime_cache

    return None


def get_data_vintage() -> dict:
    try:
        df = load_t100_data()
        years = sorted(df["year"].unique()) if "year" in df.columns else []
        months = sorted(df["month"].unique()) if "month" in df.columns else []
        latest_year = int(years[-1]) if years else None
        latest_month = int(months[-1]) if months else None
        return {
            "source": "BTS T-100 Domestic Segment",
            "years_covered": [int(y) for y in years],
            "latest_period": f"{latest_year}-{latest_month:02d}" if latest_year and latest_month else "unknown",
            "record_count": len(df),
        }
    except FileNotFoundError:
        return {
            "source": "BTS T-100 Domestic Segment",
            "years_covered": [],
            "latest_period": "no data loaded",
            "record_count": 0,
        }


def clear_cache() -> None:
    global _t100_cache, _ontime_cache
    _t100_cache = None
    _ontime_cache = None
