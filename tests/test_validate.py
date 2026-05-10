from datetime import date
from decimal import Decimal

import pytest

from whoberi.types import Entry
from whoberi.validate import (
    validate_column_names,
    validate_entries,
    validate_entry,
)

REGISTRY = [
    "assets:venn-cad",
    "income",
    "expenses",
    "tax:hst-collected",
    "tax:hst-paid",
    "liabilities:cra-tax",
    "equity:draws",
]


def entry(accounts: dict[str, Decimal], desc: str = "test", d: date = date(2026, 1, 1)) -> Entry:
    return Entry(date=d, accounts=accounts, meta={"description": desc})


# --- Per-entry ---

def test_balanced_entry_no_errors():
    e = entry({"a": Decimal("100"), "b": Decimal("-100")})
    assert validate_entry(e) == []


def test_unbalanced_entry_error():
    e = entry({"a": Decimal("100"), "b": Decimal("-99")})
    errors = validate_entry(e)
    assert len(errors) == 1
    assert "off by" in errors[0]


def test_unknown_account_flagged():
    e = entry({"assets:venn-cad": Decimal("100"), "assets:unknown": Decimal("-100")})
    errors = validate_entry(e, REGISTRY)
    assert any("unknown account" in err for err in errors)


def test_prefix_account_allowed():
    e = entry({"expenses:meals": Decimal("50"), "assets:venn-cad": Decimal("-50")})
    errors = validate_entry(e, REGISTRY)
    assert errors == []


def test_exact_account_allowed():
    e = entry({"tax:hst-paid": Decimal("10"), "assets:venn-cad": Decimal("-10")})
    errors = validate_entry(e, REGISTRY)
    assert errors == []


# --- Duplicate detection ---

def test_duplicate_detected():
    e1 = entry({"a": Decimal("100"), "b": Decimal("-100")}, desc="same")
    e2 = entry({"a": Decimal("100"), "b": Decimal("-100")}, desc="same")
    errors = validate_entries([e1, e2])
    assert any("Duplicate" in err for err in errors)


def test_different_entries_not_duplicate():
    e1 = entry({"a": Decimal("100"), "b": Decimal("-100")}, desc="one")
    e2 = entry({"a": Decimal("200"), "b": Decimal("-200")}, desc="two")
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
    if valid:
        assert result == []
    else:
        assert result == [col]
