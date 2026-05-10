import csv
from pathlib import Path

import pytest

from whoberi.heal import heal_csv


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "description", "amount"])
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


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
    write_csv(path, rows)
    logs = heal_csv(path)
    assert any("sorted" in msg for msg in logs)
    result = read_csv(path)
    assert [r["date"] for r in result] == expected_dates


def test_duplicate_removed(tmp_path):
    path = tmp_path / "ledger.csv"
    row = {"date": "2026-01-01", "description": "AWS", "amount": "100"}
    write_csv(path, [row, row])
    logs = heal_csv(path)
    assert any("duplicate" in msg for msg in logs)
    assert len(read_csv(path)) == 1


def test_clean_csv_unchanged(tmp_path):
    path = tmp_path / "ledger.csv"
    rows = [
        {"date": "2026-01-01", "description": "A", "amount": "10"},
        {"date": "2026-02-01", "description": "B", "amount": "20"},
    ]
    write_csv(path, rows)
    original_mtime = path.stat().st_mtime
    logs = heal_csv(path)
    assert logs == []
    assert path.stat().st_mtime == original_mtime


def test_duplicate_and_out_of_order(tmp_path):
    path = tmp_path / "ledger.csv"
    row_b = {"date": "2026-02-01", "description": "B", "amount": "20"}
    row_a = {"date": "2026-01-01", "description": "A", "amount": "10"}
    write_csv(path, [row_b, row_a, row_b])  # out-of-order + duplicate
    logs = heal_csv(path)
    assert any("duplicate" in msg for msg in logs)
    assert any("sorted" in msg for msg in logs)
    result = read_csv(path)
    assert len(result) == 2
    assert result[0]["date"] == "2026-01-01"
    assert result[1]["date"] == "2026-02-01"
