from pathlib import Path

import pytest

from whoberi.discover import discover

FIXTURES = Path(__file__).parent / "fixtures"


def test_handler_in_same_dir():
    results = discover(FIXTURES)
    paths = {r[0] for r in results}
    assert FIXTURES / "income" / "fooco.csv" in paths
    assert FIXTURES / "income" / "barco.csv" in paths


def test_handler_inherited_from_parent():
    """expenses/software.csv should use expenses/handler.py (same dir)."""
    results = discover(FIXTURES)
    by_path = {r[0]: r[1] for r in results}
    software_handler = by_path[FIXTURES / "expenses" / "software.csv"]
    assert software_handler.__file__ == str(FIXTURES / "expenses" / "handler.py")


def test_handler_overridden_by_child():
    """expenses/travel/flights.csv should use expenses/travel/handler.py, not expenses/handler.py."""
    results = discover(FIXTURES)
    by_path = {r[0]: r[1] for r in results}
    flights_handler = by_path[FIXTURES / "expenses" / "travel" / "flights.csv"]
    assert flights_handler.__file__ == str(FIXTURES / "expenses" / "travel" / "handler.py")


def test_imports_dir_skipped():
    """CSVs under imports/ should not appear in results."""
    results = discover(FIXTURES)
    paths = {r[0] for r in results}
    assert not any("imports" in str(p) for p in paths)


def test_toml_overrides_loaded():
    """barco.toml overrides should appear in barco's LedgerMeta."""
    results = discover(FIXTURES)
    by_name = {r[2].name: r[2] for r in results}
    assert by_name["barco"].overrides == {"currency": "USD", "tax_applies": False}


def test_no_overrides_when_toml_absent():
    results = discover(FIXTURES)
    by_name = {r[2].name: r[2] for r in results}
    assert by_name["fooco"].overrides == {}


def test_missing_handler_raises():
    """A CSV with no handler anywhere in the tree should raise FileNotFoundError."""
    tmp = Path(__file__).parent / "fixtures_no_handler"
    tmp.mkdir(exist_ok=True)
    csv = tmp / "orphan.csv"
    csv.write_text("date\n2026-01-01\n")
    try:
        with pytest.raises(FileNotFoundError, match="No handler.py found"):
            discover(tmp)
    finally:
        csv.unlink()
        tmp.rmdir()


def test_ledger_meta_fields():
    results = discover(FIXTURES)
    by_name = {r[2].name: r[2] for r in results}
    meta = by_name["software"]
    assert meta.name == "software"
    assert meta.directory == "expenses"
    assert meta.path == FIXTURES / "expenses" / "software.csv"
