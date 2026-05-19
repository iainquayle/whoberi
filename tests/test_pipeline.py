"""Integration test: discover -> process -> aggregate -> balance = 0."""
from whoberi.aggregate import check_balance, is_balanced
from whoberi.main import run_pipeline
from tests.conftest import FIXTURES


def test_pipeline_all_entries_balanced():
    result = run_pipeline(FIXTURES)
    assert len(result.entries) > 0
    assert all(is_balanced(e, result.registry) for e in result.entries)
    assert check_balance(result.combined, result.registry) == 0
