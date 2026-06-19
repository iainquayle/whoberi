"""Round-trip the delimited-file IO for each supported extension."""
import pytest

from whoberi.ledgers.delimited_io import (
    DELIMITERS,
    delimiter_for,
    infer_extension,
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


def test_delimiter_for_unknown_raises(tmp_path):
    with pytest.raises(ValueError, match="unsupported ledger extension"):
        delimiter_for(tmp_path / "x.txt")


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


# --- header sanity check ---

@pytest.mark.parametrize("declared,actual_ext", [
    (".tsv", ".csv"),
    (".psv", ".csv"),
    (".csv", ".tsv"),
    (".csv", ".psv"),
])
def test_wrong_delimiter_raises(tmp_path, declared, actual_ext):
    """Reading a file with a header that uses another supported delimiter raises."""
    path = tmp_path / f"ledger{declared}"
    path.write_text(DELIMITERS[actual_ext].join(FIELDS) + "\n")
    with pytest.raises(ValueError, match="wrong extension"):
        list(read_rows(path))


def test_single_column_file_allowed(tmp_path):
    """A legitimate single-column file passes the header check."""
    path = tmp_path / "single.csv"
    path.write_text("date\n2026-01-01\n")
    assert list(read_rows(path)) == [{"date": "2026-01-01"}]


# --- infer_extension ---

def test_infer_extension_empty_tree_defaults_csv(tmp_path):
    assert infer_extension(tmp_path) == ".csv"


@pytest.mark.parametrize("dominant", sorted(DELIMITERS))
def test_infer_extension_picks_dominant(tmp_path, dominant):
    for i in range(3):
        (tmp_path / f"l{i}{dominant}").write_text("date\n")
    minority = next(e for e in DELIMITERS if e != dominant)
    (tmp_path / f"other{minority}").write_text("date\n")
    assert infer_extension(tmp_path) == dominant


def test_infer_extension_recursive(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.tsv").write_text("date\n")
    (tmp_path / "sub" / "b.tsv").write_text("date\n")
    (tmp_path / "c.csv").write_text("date\n")
    assert infer_extension(tmp_path) == ".tsv"
