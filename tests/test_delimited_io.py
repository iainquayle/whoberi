"""Round-trip the delimited-file IO for each supported extension."""
import pytest

from whoberi.ledgers.delimited_io import (
    DELIMITERS,
    read_headers,
    read_rows,
    read_rows_with_headers,
    resolve_existing,
    write_rows,
)


ROWS = [
    {"date": "2026-01-01", "description": "A", "amount": "10"},
    {"date": "2026-01-02", "description": "B", "amount": "20"},
]
FIELDS = ["date", "description", "amount"]


@pytest.mark.parametrize("suffix", sorted(DELIMITERS))
def test_round_trip(tmp_path, suffix):
    path = tmp_path / f"ledger{suffix}"
    write_rows(path, FIELDS, ROWS)
    raw = path.read_text()
    assert DELIMITERS[suffix].join(FIELDS) in raw.splitlines()[0]
    assert read_headers(path) == FIELDS
    assert list(read_rows(path)) == ROWS
    assert read_rows_with_headers(path) == (FIELDS, ROWS)


def test_unknown_extension_raises(tmp_path):
    path = tmp_path / "ledger.txt"
    with pytest.raises(ValueError, match="unsupported ledger extension"):
        write_rows(path, FIELDS, ROWS)


def test_resolve_existing_none(tmp_path):
    assert resolve_existing(tmp_path, "ghost") is None


@pytest.mark.parametrize("suffix", sorted(DELIMITERS))
def test_resolve_existing_match(tmp_path, suffix):
    path = tmp_path / f"foo{suffix}"
    path.write_text("date\n")
    assert resolve_existing(tmp_path, "foo") == path


def test_resolve_existing_ambiguous(tmp_path):
    (tmp_path / "foo.csv").write_text("date\n")
    (tmp_path / "foo.tsv").write_text("date\n")
    with pytest.raises(ValueError, match="Ambiguous ledger 'foo'"):
        resolve_existing(tmp_path, "foo")
