import pytest

from whoberi.discover import read_csv
from whoberi.heal import heal_csv
from tests.conftest import CSV_FIELDS, write_csv


@pytest.mark.parametrize("rows,expected_dates", [
    (
        [
            {"date": "2026-01-15", "description": "B", "amount": "50"},
            {"date": "2026-01-01", "description": "A", "amount": "100"},
        ],
        ["2026-01-01", "2026-01-15"],
    ),
    (
        [
            {"date": "2026-03-01", "description": "C", "amount": "30"},
            {"date": "2026-01-01", "description": "A", "amount": "10"},
            {"date": "2026-02-01", "description": "B", "amount": "20"},
        ],
        ["2026-01-01", "2026-02-01", "2026-03-01"],
    ),
])
def test_out_of_order_sorted(tmp_path, rows, expected_dates):
    path = tmp_path / "ledger.csv"
    write_csv(path, CSV_FIELDS, rows)
    logs = heal_csv(path)
    assert any("sorted" in msg for msg in logs)
    result = read_csv(path)
    assert [r["date"] for r in result] == expected_dates


def test_duplicate_removed(tmp_path):
    path = tmp_path / "ledger.csv"
    row = {"date": "2026-01-01", "description": "AWS", "amount": "100"}
    write_csv(path, CSV_FIELDS, [row, row])
    logs = heal_csv(path)
    assert any("duplicate" in msg for msg in logs)
    assert len(read_csv(path)) == 1


def test_clean_csv_unchanged(tmp_path):
    path = tmp_path / "ledger.csv"
    rows = [
        {"date": "2026-01-01", "description": "A", "amount": "10"},
        {"date": "2026-02-01", "description": "B", "amount": "20"},
    ]
    write_csv(path, CSV_FIELDS, rows)
    original_mtime = path.stat().st_mtime
    logs = heal_csv(path)
    assert logs == []
    assert path.stat().st_mtime == original_mtime


def test_duplicate_and_out_of_order(tmp_path):
    path = tmp_path / "ledger.csv"
    row_b = {"date": "2026-02-01", "description": "B", "amount": "20"}
    row_a = {"date": "2026-01-01", "description": "A", "amount": "10"}
    write_csv(path, CSV_FIELDS, [row_b, row_a, row_b])
    logs = heal_csv(path)
    assert any("duplicate" in msg for msg in logs)
    assert any("sorted" in msg for msg in logs)
    result = read_csv(path)
    assert len(result) == 2
    assert result[0]["date"] == "2026-01-01"
    assert result[1]["date"] == "2026-02-01"


def test_missing_date_raises(tmp_path):
    path = tmp_path / "ledger.csv"
    write_csv(path, ["description", "amount"], [{"description": "AWS", "amount": "100"}])
    with pytest.raises(KeyError):
        heal_csv(path)
