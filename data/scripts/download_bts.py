"""
Download BTS T-100 Domestic Segment data via the Socrata Open Data API (SODA).

Dataset: AFF - T100 Segment Summary By Origin Airport
Endpoint: https://data.bts.gov/resource/r495-tyji

Usage:
    python -m data.scripts.download_bts           # from project root
    python data/scripts/download_bts.py            # direct

Downloads the most recent N years of data (configurable via BTS_DATA_YEARS env var).
Falls back to fewer years if download times out.
Saves raw CSV to data/raw/ and converts to Parquet in data/processed/.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings, RAW_DIR, PROCESSED_DIR

SODA_ENDPOINT = "https://data.bts.gov/resource/r495-tyji.json"
PAGE_SIZE = 50000
CURRENT_YEAR = 2026


def download_year(year: int, timeout: int) -> pd.DataFrame | None:
    print(f"  Downloading {year}...")
    all_rows: list[dict] = []
    offset = 0
    client = httpx.Client(timeout=timeout)

    try:
        while True:
            params = {
                "$where": f"year='{year}'",
                "$limit": str(PAGE_SIZE),
                "$offset": str(offset),
                "$order": "origin_airport_code,reporting_month",
            }
            resp = client.get(SODA_ENDPOINT, params=params)
            resp.raise_for_status()
            rows = resp.json()

            if not rows:
                break

            all_rows.extend(rows)
            print(f"    fetched {len(all_rows)} rows so far...")
            offset += PAGE_SIZE

            if len(rows) < PAGE_SIZE:
                break

    except httpx.TimeoutException:
        print(f"  Timeout after {len(all_rows)} rows for {year}")
        if all_rows:
            return pd.DataFrame(all_rows)
        return None
    except httpx.HTTPStatusError as e:
        print(f"  HTTP error for {year}: {e.response.status_code}")
        return None
    finally:
        client.close()

    if not all_rows:
        print(f"  No data found for {year}")
        return None

    print(f"  Got {len(all_rows)} rows for {year}")
    return pd.DataFrame(all_rows)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip() for c in df.columns]

    rename = {
        "origin_airport_code": "origin",
        "origin_airport_name": "airport_name",
        "origin_city_name": "city_name",
        "domestic_passengers": "passengers",
        "domestic_seats": "seats",
        "domestic_departures": "departures_performed",
        "domestic_freight_lbs": "freight",
        "domestic_distance_flight": "distance",
        "total_departures": "total_departures_all",
        "total_passengers": "total_passengers_all",
        "total_seats": "total_seats_all",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    if "departures_performed" in df.columns:
        df["departures_scheduled"] = df["departures_performed"]

    if "reporting_month" in df.columns and "month" not in df.columns:
        df["month"] = pd.to_datetime(df["reporting_month"], errors="coerce").dt.month

    numeric_cols = [
        "passengers", "freight", "seats",
        "departures_performed", "departures_scheduled",
        "year", "month", "distance",
        "total_departures_all", "total_passengers_all", "total_seats_all",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            if col not in ("distance",):
                df[col] = df[col].astype(int)

    return df


def save_data(df: pd.DataFrame, year: int) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = RAW_DIR / f"t100_{year}.csv"
    parquet_path = PROCESSED_DIR / f"t100_{year}.parquet"

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    print(f"  Saved: {csv_path.name} ({len(df)} rows), {parquet_path.name}")


def main() -> None:
    n_years = settings.bts_data_years
    timeout = settings.bts_download_timeout

    target_years = list(range(CURRENT_YEAR - n_years, CURRENT_YEAR))
    print(f"BTS T-100 Downloader")
    print(f"  Target years: {target_years}")
    print(f"  Timeout per year: {timeout}s")
    print(f"  Endpoint: {SODA_ENDPOINT}")
    print()

    downloaded = 0
    for year in reversed(target_years):
        start = time.time()
        df = download_year(year, timeout)
        elapsed = time.time() - start

        if df is not None and len(df) > 0:
            df = normalize_columns(df)
            save_data(df, year)
            downloaded += 1
            print(f"  Completed {year} in {elapsed:.1f}s")
        else:
            print(f"  Skipping {year} (no data or timeout)")

            if downloaded == 0:
                print(f"  Trying with reduced timeout...")
                continue

        print()

    if downloaded == 0:
        print("WARNING: No data downloaded. Check your network connection.")
        print("You can also manually download from https://transtats.bts.gov/")
        print("Place CSV files as data/raw/t100_YYYY.csv")
        sys.exit(1)

    print(f"Done. Downloaded {downloaded} year(s) of T-100 data.")


if __name__ == "__main__":
    main()
