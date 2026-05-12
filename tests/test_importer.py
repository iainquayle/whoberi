import csv
from pathlib import Path

import pytest

from whoberi.ledgers.importer import import_bank_csv
from tests.conftest import CSV_FIELDS, write_csv

RULES = {
    "AWS": "expenses/software",
    "UBER EATS": "expenses/meals",
    "E-TRANSFER FROM": "income/fooco",
}


@pytest.fixture
def tmp_root(tmp_path):
    (tmp_path / "expenses").mkdir()
    (tmp_path / "income").mkdir()
    return tmp_path


def test_matched_row_appended(tmp_root):
    bank = tmp_root / "bank.csv"
    write_csv(bank, CSV_FIELDS, [{"date": "2026-01-01", "description": "AWS", "amount": "157.50"}])

    matched, unmatched = import_bank_csv(bank, RULES, tmp_root)

    assert len(matched) == 1
    assert unmatched == []
    target = tmp_root / "expenses" / "software.csv"
    assert target.exists()
    rows = list(csv.DictReader(open(target)))
    assert len(rows) == 1
    assert rows[0]["description"] == "AWS"


def test_unmatched_row_returned(tmp_root):
    bank = tmp_root / "bank.csv"
    write_csv(bank, CSV_FIELDS, [{"date": "2026-01-01", "description": "MYSTERY VENDOR", "amount": "99.00"}])

    matched, unmatched = import_bank_csv(bank, RULES, tmp_root)

    assert matched == []
    assert len(unmatched) == 1
    assert not (tmp_root / "expenses" / "software.csv").exists()


def test_duplicate_not_appended(tmp_root):
    bank = tmp_root / "bank.csv"
    row = {"date": "2026-01-01", "description": "AWS", "amount": "157.50"}
    write_csv(bank, CSV_FIELDS, [row])

    import_bank_csv(bank, RULES, tmp_root)
    import_bank_csv(bank, RULES, tmp_root)

    target = tmp_root / "expenses" / "software.csv"
    rows = list(csv.DictReader(open(target)))
    assert len(rows) == 1  # not doubled


def test_case_insensitive_pattern_match(tmp_root):
    bank = tmp_root / "bank.csv"
    write_csv(bank, CSV_FIELDS, [{"date": "2026-01-01", "description": "aws charges", "amount": "50.00"}])

    matched, unmatched = import_bank_csv(bank, RULES, tmp_root)

    assert len(matched) == 1
    assert unmatched == []


def test_multiple_rows_mixed(tmp_root):
    bank = tmp_root / "bank.csv"
    write_csv(bank, CSV_FIELDS, [
        {"date": "2026-01-01", "description": "AWS", "amount": "157.50"},
        {"date": "2026-01-02", "description": "RANDOM CO", "amount": "500.00"},
        {"date": "2026-01-03", "description": "UBER EATS", "amount": "45.00"},
    ])

    matched, unmatched = import_bank_csv(bank, RULES, tmp_root)

    assert len(matched) == 2
    assert len(unmatched) == 1
