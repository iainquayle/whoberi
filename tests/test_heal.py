from datetime import date

import pytest

from whoberi.ledgers.delimited_io import read_rows
from whoberi.ledgers.heal import heal, heal_file
from tests.conftest import CSV_FIELDS, write_csv


# --- Pure heal ---

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
def test_heal_sorts(rows, expected_dates):
    healed, logs = heal(rows)
    healed_list = list(healed)
    assert any("sorted" in m for m in logs)
    assert [r["date"] for r in healed_list] == expected_dates


def test_heal_removes_duplicates():
    row = {"date": "2026-01-01", "description": "AWS", "amount": "100"}
    healed, logs = heal([row, row])
    assert any("duplicate" in m for m in logs)
    assert len(list(healed)) == 1


def test_heal_clean_input_no_logs():
    rows = [
        {"date": "2026-01-01", "description": "A", "amount": "10"},
        {"date": "2026-02-01", "description": "B", "amount": "20"},
    ]
    healed, logs = heal(rows)
    assert logs == []
    assert list(healed) == rows


def test_heal_empty_input():
    healed, logs = heal([])
    assert logs == []
    assert list(healed) == []


def test_heal_accepts_iterable():
    """heal should work on a generator, not just a list."""
    def gen():
        yield {"date": "2026-02-01", "description": "B", "amount": "20"}
        yield {"date": "2026-01-01", "description": "A", "amount": "10"}
    healed, logs = heal(gen())
    assert [r["date"] for r in healed] == ["2026-01-01", "2026-02-01"]
    assert any("sorted" in m for m in logs)


# --- heal_file (IO orchestrator) ---

def test_heal_file_writes_when_changed(tmp_path):
    path = tmp_path / "ledger.csv"
    write_csv(path, CSV_FIELDS, [
        {"date": "2026-02-01", "description": "B", "amount": "20"},
        {"date": "2026-01-01", "description": "A", "amount": "10"},
    ])
    logs = heal_file(path)
    assert logs and "sorted" in logs[0]
    result = list(read_rows(path))
    assert [r["date"] for r in result] == ["2026-01-01", "2026-02-01"]


def test_heal_file_clean_no_rewrite(tmp_path):
    path = tmp_path / "ledger.csv"
    write_csv(path, CSV_FIELDS, [
        {"date": "2026-01-01", "description": "A", "amount": "10"},
        {"date": "2026-02-01", "description": "B", "amount": "20"},
    ])
    mtime = path.stat().st_mtime
    assert heal_file(path) == []
    assert path.stat().st_mtime == mtime


def test_heal_file_missing_path_no_op(tmp_path):
    assert heal_file(tmp_path / "missing.csv") == []


def test_heal_file_missing_date_raises(tmp_path):
    path = tmp_path / "ledger.csv"
    write_csv(path, ["description", "amount"], [{"description": "AWS", "amount": "100"}])
    with pytest.raises(KeyError):
        heal_file(path)


def test_heal_rejects_non_iso_date():
    rows = [
        {"date": "01/15/2026", "description": "A", "amount": "10"},
        {"date": "01/01/2026", "description": "B", "amount": "20"},
    ]
    with pytest.raises(ValueError, match="not ISO 8601"):
        heal(rows)
