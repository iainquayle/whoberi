import pytest

from whoberi.discover import discover
from tests.conftest import FIXTURES


def test_handler_in_same_dir():
    results = discover(FIXTURES)
    by_path = {r[0]: r[1] for r in results}
    assert FIXTURES / "income" / "fooco.csv" in by_path
    assert FIXTURES / "income" / "barco.csv" in by_path
    assert by_path[FIXTURES / "income" / "fooco.csv"].__file__ == str(FIXTURES / "income" / "fooco.py")
    assert by_path[FIXTURES / "income" / "barco.csv"].__file__ == str(FIXTURES / "income" / "barco.py")


def test_imports_dir_skipped():
    results = discover(FIXTURES)
    paths = {r[0] for r in results}
    assert not any("imports" in str(p) for p in paths)


def test_missing_handler_raises(tmp_path):
    (tmp_path / "orphan.csv").write_text("date\n2026-01-01\n")
    with pytest.raises(FileNotFoundError, match="Missing handler: expected"):
        discover(tmp_path)


def test_orphan_handler_raises(tmp_path):
    (tmp_path / "stray.py").write_text("def process(rows, config, meta): return iter(())\n")
    with pytest.raises(FileNotFoundError, match="Orphan handler"):
        discover(tmp_path)


def test_combined_errors_reported(tmp_path):
    (tmp_path / "nohandler.csv").write_text("date\n2026-01-01\n")
    (tmp_path / "nocsv.py").write_text("def process(rows, config, meta): return iter(())\n")
    with pytest.raises(FileNotFoundError) as exc_info:
        discover(tmp_path)
    msg = str(exc_info.value)
    assert "Missing handler" in msg
    assert "Orphan handler" in msg


def test_ledger_meta_fields():
    results = discover(FIXTURES)
    by_name = {r[2].name: r[2] for r in results}
    meta = by_name["software"]
    assert meta.name == "software"
    assert meta.directory == "expenses"
    assert meta.path == FIXTURES / "expenses" / "software.csv"
