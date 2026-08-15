from __future__ import annotations

import json
from typing import Optional

import pandas as pd

from backend.config import REFERENCE_DIR

_msa_data: Optional[pd.DataFrame] = None
_msa_mapping: Optional[dict[str, str]] = None


def _load() -> None:
    global _msa_data, _msa_mapping
    if _msa_data is not None:
        return

    csv_path = REFERENCE_DIR / "msa_population.csv"
    mapping_path = REFERENCE_DIR / "msa_to_airport.json"

    _msa_data = pd.read_csv(csv_path)

    with open(mapping_path) as f:
        _msa_mapping = json.load(f)


def get_msa_for_airport(iata: str) -> Optional[str]:
    _load()
    return _msa_mapping.get(iata.upper())


def get_msa_population(msa_name: str) -> Optional[dict]:
    _load()
    row = _msa_data[_msa_data["msa_name"] == msa_name]
    if row.empty:
        return None

    row = row.iloc[0]
    pop_cols = [c for c in _msa_data.columns if c.startswith("pop_")]
    years = sorted(pop_cols)

    populations = {col.replace("pop_", ""): int(row[col]) for col in years}
    year_keys = sorted(populations.keys())

    if len(year_keys) >= 2:
        first_year, last_year = year_keys[0], year_keys[-1]
        first_pop, last_pop = populations[first_year], populations[last_year]
        n_years = int(last_year) - int(first_year)
        if n_years > 0 and first_pop > 0:
            cagr = (last_pop / first_pop) ** (1 / n_years) - 1
        else:
            cagr = 0.0
    else:
        cagr = 0.0

    airports_str = row.get("airports", "")
    airports = airports_str.split("|") if airports_str else []

    return {
        "msa_name": msa_name,
        "airports": airports,
        "populations": populations,
        "cagr": round(cagr, 6),
        "latest_population": populations[year_keys[-1]] if year_keys else None,
    }


def get_airport_msa_growth(iata: str) -> Optional[dict]:
    msa_name = get_msa_for_airport(iata)
    if not msa_name:
        return None
    return get_msa_population(msa_name)
