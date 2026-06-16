import pytest

from whoberi.ledgers.handler_discovery import discover
from tests.conftest import FIXTURES

BOOKS = FIXTURES / "books"


def test_handler_in_same_dir():
    results = discover(BOOKS)
    by_path = {r[0]: r[1] for r in results}
    assert BOOKS / "income" / "fooco.csv" in by_path
    assert BOOKS / "income" / "barco.csv" in by_path
    assert by_path[BOOKS / "income" / "fooco.csv"].__file__ == str(BOOKS / "income" / "fooco.py")
    assert by_path[BOOKS / "income" / "barco.csv"].__file__ == str(BOOKS / "income" / "barco.py")


def test_missing_handler_raises(tmp_path):
    (tmp_path / "orphan.csv").write_text("date\n2026-01-01\n")
    with pytest.raises(ValueError, match="Missing handler: expected"):
        discover(tmp_path)


def test_orphan_handler_raises(tmp_path):
    (tmp_path / "stray.py").write_text("def process(rows, config, meta): return iter(())\n")
    with pytest.raises(ValueError, match="Orphan handler"):
        discover(tmp_path)


def test_combined_errors_reported(tmp_path):
    (tmp_path / "nohandler.csv").write_text("date\n2026-01-01\n")
    (tmp_path / "nocsv.py").write_text("def process(rows, config, meta): return iter(())\n")
    with pytest.raises(ValueError) as exc_info:
        discover(tmp_path)
    msg = str(exc_info.value)
    assert "Missing handler" in msg
    assert "Orphan handler" in msg


def test_handler_with_syntax_error_raises_clear_error(tmp_path):
    (tmp_path / "bad.csv").write_text("date\n")
    (tmp_path / "bad.py").write_text("this is not python!!!\n")
    with pytest.raises(ValueError, match="Failed to load handler 'bad.py'"):
        discover(tmp_path)


@pytest.mark.parametrize("suffix", [".csv", ".tsv", ".psv"])
def test_discovers_each_supported_extension(tmp_path, suffix):
    (tmp_path / f"foo{suffix}").write_text("date\n2026-01-01\n")
    (tmp_path / "foo.py").write_text("def process(rows, config, meta): return iter(())\n")
    results = discover(tmp_path)
    assert [r[0] for r in results] == [tmp_path / f"foo{suffix}"]


def test_ambiguous_stems_raise(tmp_path):
    (tmp_path / "foo.csv").write_text("date\n")
    (tmp_path / "foo.tsv").write_text("date\n")
    (tmp_path / "foo.py").write_text("def process(rows, config, meta): return iter(())\n")
    with pytest.raises(ValueError, match="Ambiguous ledger files"):
        discover(tmp_path)


def test_ledger_meta_fields():
    results = discover(BOOKS)
    by_name = {r[2].name: r[2] for r in results}
    meta = by_name["software"]
    assert meta.name == "software"
    assert meta.directory == "expenses"
    assert meta.path == BOOKS / "expenses" / "software.csv"
