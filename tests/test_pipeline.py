"""Integration test: discover -> process -> aggregate -> balance = 0."""
from whoberi.aggregate import aggregate, check_balance
from whoberi.config import load_config
from whoberi.discover import discover, read_csv
from tests.conftest import FIXTURES


def run_pipeline(root):
    config = load_config(root)
    ledgers = discover(root)
    entries = []
    for csv_path, handler, meta in ledgers:
        rows = read_csv(csv_path)
        entries.extend(handler.process(rows, config, meta))
    combined = aggregate(entries)
    return entries, combined


def test_pipeline_all_entries_balanced():
    entries, combined = run_pipeline(FIXTURES)
    assert len(entries) > 0
    assert all(e.balanced for e in entries)
    assert check_balance(combined) == 0
