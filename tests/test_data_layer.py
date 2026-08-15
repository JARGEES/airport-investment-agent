"""Quick validation of the M1 data layer modules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.data.airports import (
    get_airport,
    get_airports_by_region,
    get_airports_by_state,
    search_airports,
    get_all_airports,
    get_all_regions,
)
from backend.data.census import get_msa_for_airport, get_airport_msa_growth
from backend.config import settings


def test_airport_lookup():
    bos = get_airport("BOS")
    assert bos is not None
    assert bos.name == "Boston Logan International"
    assert bos.state == "MA"
    assert bos.hub_size == "large_hub"
    print(f"  [PASS] Airport lookup: {bos.iata} = {bos.name}")


def test_region_lookup():
    ne_airports = get_airports_by_region("New England")
    assert len(ne_airports) > 0
    states = {a.state for a in ne_airports}
    assert "MA" in states
    assert "CT" in states
    print(f"  [PASS] New England airports: {len(ne_airports)} found — {[a.iata for a in ne_airports]}")


def test_state_lookup():
    ca_airports = get_airports_by_state("CA")
    assert len(ca_airports) > 0
    assert any(a.iata == "LAX" for a in ca_airports)
    print(f"  [PASS] California airports: {len(ca_airports)} found")


def test_search():
    results = search_airports(min_passengers=20000000)
    assert len(results) > 5
    assert results[0].estimated_annual_pax >= results[-1].estimated_annual_pax
    print(f"  [PASS] Search (20M+ pax): {len(results)} airports, top = {results[0].iata}")


def test_all_airports_mode():
    all_a = get_all_airports(respect_mode=False)
    fast_a = get_all_airports(respect_mode=True)
    if settings.fast_mode:
        assert len(fast_a) <= 100
        assert len(all_a) > len(fast_a)
        print(f"  [PASS] Mode filtering: fast={len(fast_a)}, all={len(all_a)}")
    else:
        print(f"  [PASS] Mode filtering: deep mode, all={len(all_a)}")


def test_regions():
    regions = get_all_regions()
    assert "New England" in regions
    assert "Pacific West" in regions
    print(f"  [PASS] Regions loaded: {list(regions.keys())}")


def test_msa_mapping():
    msa = get_msa_for_airport("SFO")
    assert msa is not None
    assert "San Francisco" in msa
    print(f"  [PASS] MSA mapping: SFO → {msa}")


def test_msa_growth():
    growth = get_airport_msa_growth("ATL")
    assert growth is not None
    assert growth["cagr"] != 0
    print(f"  [PASS] MSA growth: ATL CAGR = {growth['cagr']:.4%}")


def main():
    print("M1 Data Layer Validation")
    print("=" * 50)
    tests = [
        test_airport_lookup,
        test_region_lookup,
        test_state_lookup,
        test_search,
        test_all_airports_mode,
        test_regions,
        test_msa_mapping,
        test_msa_growth,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
