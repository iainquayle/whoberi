from decimal import Decimal

import pytest

from whoberi.validate import validate_column_names, validate_entries, validate_entry
from tests.conftest import make_entry

REGISTRY = [
    "assets:venn-cad",
    "income",
    "expenses",
    "tax:hst-collected",
    "tax:hst-paid",
    "liabilities:cra-tax",
    "equity:draws",
]


# --- Per-entry ---

def test_balanced_entry_no_errors():
    assert validate_entry(make_entry({"a": Decimal("100"), "b": Decimal("-100")})) == []


def test_unbalanced_entry_error():
    errors = validate_entry(make_entry({"a": Decimal("100"), "b": Decimal("-99")}))
    assert len(errors) == 1
    assert "off by" in errors[0]


@pytest.mark.parametrize("accounts,expected_error", [
    ({"assets:venn-cad": Decimal("100"), "assets:unknown": Decimal("-100")}, "unknown account"),
    ({"expenses:meals": Decimal("50"), "assets:venn-cad": Decimal("-50")}, None),
    ({"tax:hst-paid": Decimal("10"), "assets:venn-cad": Decimal("-10")}, None),
])
def test_account_registry(accounts, expected_error):
    errors = validate_entry(make_entry(accounts), REGISTRY)
    if expected_error:
        assert any(expected_error in e for e in errors)
    else:
        assert errors == []


# --- Duplicate detection ---

def test_duplicate_detected():
    e1 = make_entry({"a": Decimal("100"), "b": Decimal("-100")}, desc="same")
    e2 = make_entry({"a": Decimal("100"), "b": Decimal("-100")}, desc="same")
    assert any("Duplicate" in err for err in validate_entries([e1, e2]))


def test_different_entries_not_duplicate():
    e1 = make_entry({"a": Decimal("100"), "b": Decimal("-100")}, desc="one")
    e2 = make_entry({"a": Decimal("200"), "b": Decimal("-200")}, desc="two")
    assert validate_entries([e1, e2]) == []


# --- Column name validation ---

@pytest.mark.parametrize("col,valid", [
    ("date", True),
    ("invoice-id", True),
    ("amount", True),
    ("receipt-number", True),
    ("Amount", False),
    ("invoice_id", False),
    ("2bad", False),
    ("", False),
])
def test_column_name_validation(col, valid):
    result = validate_column_names([col])
    assert result == ([] if valid else [col])
