"""Integration test: discover -> process -> aggregate -> balance = 0."""
from pathlib import Path

from whoberi.aggregate import aggregate, check_balance
from whoberi.config import load_config
from whoberi.discover import discover, read_csv

FIXTURES = Path(__file__).parent / "fixtures"


def run_pipeline(root: Path):
    config = load_config(root)
    ledgers = discover(root, config)
    entries = []
    for csv_path, handler, meta in ledgers:
        rows = read_csv(csv_path)
        entries.extend(handler.process(rows, config, meta))
    combined = aggregate(entries)
    return entries, combined


def test_pipeline_balances():
    entries, combined = run_pipeline(FIXTURES)
    assert len(entries) > 0
    assert check_balance(combined) == 0


def test_pipeline_expense_entries_balanced():
    _, combined = run_pipeline(FIXTURES)
    # Each individual entry should be balanced (checked via property)
    entries, _ = run_pipeline(FIXTURES)
    unbalanced = [e for e in entries if not e.balanced]
    assert unbalanced == []


def test_expense_handler_produces_correct_accounts():
    config = load_config(FIXTURES)
    ledgers = discover(FIXTURES, config)
    by_name = {meta.name: (csv_path, handler, meta) for csv_path, handler, meta in ledgers}

    csv_path, handler, meta = by_name["software"]
    rows = read_csv(csv_path)
    entries = list(handler.process(rows, config, meta))

    assert len(entries) == 2
    for entry in entries:
        assert entry.balanced
        assert "expenses:software" in entry.accounts
        assert "tax:hst-paid" in entry.accounts
        assert "assets:venn-cad" in entry.accounts
        assert entry.accounts["assets:venn-cad"] < 0
