from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.config import REFERENCE_DIR, settings

_airports: dict[str, Airport] = {}
_regions: dict[str, list[str]] = {}


@dataclass
class Airport:
    iata: str
    name: str
    city: str
    state: str
    lat: float
    lng: float
    hub_size: str
    runways: int
    estimated_annual_pax: int

    def to_dict(self) -> dict:
        return {
            "iata": self.iata,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "lat": self.lat,
            "lng": self.lng,
            "hub_size": self.hub_size,
            "runways": self.runways,
            "estimated_annual_pax": self.estimated_annual_pax,
        }


def _load() -> None:
    global _airports, _regions
    if _airports:
        return

    airports_path = REFERENCE_DIR / "airports.json"
    regions_path = REFERENCE_DIR / "regions.json"

    with open(airports_path) as f:
        raw = json.load(f)

    for entry in raw:
        a = Airport(
            iata=entry["iata"],
            name=entry["name"],
            city=entry["city"],
            state=entry["state"],
            lat=entry["lat"],
            lng=entry["lng"],
            hub_size=entry["hub_size"],
            runways=entry["runways"],
            estimated_annual_pax=entry["estimated_annual_pax"],
        )
        _airports[a.iata] = a

    with open(regions_path) as f:
        _regions = json.load(f)


def get_airport(iata: str) -> Optional[Airport]:
    _load()
    return _airports.get(iata.upper())


def get_all_airports(respect_mode: bool = True) -> list[Airport]:
    _load()
    airports = list(_airports.values())
    if respect_mode and settings.top_n_airports:
        airports.sort(key=lambda a: a.estimated_annual_pax, reverse=True)
        airports = airports[: settings.top_n_airports]
    return airports


def get_airports_by_state(state: str) -> list[Airport]:
    _load()
    state = state.upper()
    return [a for a in _airports.values() if a.state == state]


def get_airports_by_region(region: str) -> list[Airport]:
    _load()
    states = get_region_states(region)
    if not states:
        return []
    return [a for a in _airports.values() if a.state in states]


def get_region_states(region: str) -> list[str]:
    _load()
    for name, states in _regions.items():
        if name.lower() == region.lower():
            return states
    return []


def get_all_regions() -> dict[str, list[str]]:
    _load()
    return dict(_regions)


def search_airports(
    query: Optional[str] = None,
    region: Optional[str] = None,
    state: Optional[str] = None,
    min_passengers: Optional[int] = None,
    hub_size: Optional[str] = None,
) -> list[Airport]:
    _load()

    results = list(_airports.values())

    if region:
        states = get_region_states(region)
        if states:
            results = [a for a in results if a.state in states]

    if state:
        results = [a for a in results if a.state == state.upper()]

    if min_passengers:
        results = [a for a in results if a.estimated_annual_pax >= min_passengers]

    if hub_size:
        results = [a for a in results if a.hub_size == hub_size]

    if query:
        q = query.lower()
        results = [
            a
            for a in results
            if q in a.name.lower() or q in a.city.lower() or q in a.iata.lower()
        ]

    results.sort(key=lambda a: a.estimated_annual_pax, reverse=True)
    return results
