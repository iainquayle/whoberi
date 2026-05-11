from decimal import Decimal

import pytest

from whoberi.validate import validate_column_names, validate_entries, validate_entry
from tests.conftest import FULL_REGISTRY, make_entry


# --- Per-entry balance ---

@pytest.mark.parametrize("accounts,expected_errors,error_substring", [
    ({"venn-cad": Decimal("100"), "fooco": Decimal("-100")}, 0, None),
    ({"venn-cad": Decimal("100"), "fooco": Decimal("-99")}, 1, "off by"),
    ({"venn-cad": Decimal("100.001"), "fooco": Decimal("-100")}, 1, "off by"),
])
def test_validate_entry_balance(accounts, expected_errors, error_substring):
    errors = validate_entry(make_entry(accounts), FULL_REGISTRY)
    assert len(errors) == expected_errors
    if error_substring:
        assert any(error_substring in e for e in errors)


@pytest.mark.parametrize("accounts,expected_error", [
    ({"venn-cad": Decimal("100"), "unknown-acct": Decimal("-100")}, "unknown account"),
    ({"meals": Decimal("50"), "venn-cad": Decimal("-50")}, None),
    ({"hst-paid": Decimal("10"), "venn-cad": Decimal("-10")}, None),
])
def test_account_registry(accounts, expected_error):
    errors = validate_entry(make_entry(accounts), FULL_REGISTRY)
    if expected_error:
        assert any(expected_error in e for e in errors)
    else:
        assert errors == []


# --- Duplicate detection ---

def test_duplicate_detected():
    e1 = make_entry({"venn-cad": Decimal("100"), "fooco": Decimal("-100")}, desc="same")
    e2 = make_entry({"venn-cad": Decimal("100"), "fooco": Decimal("-100")}, desc="same")
    assert any("Duplicate" in err for err in validate_entries([e1, e2], FULL_REGISTRY))


def test_different_entries_not_duplicate():
    e1 = make_entry({"venn-cad": Decimal("100"), "fooco": Decimal("-100")}, desc="one")
    e2 = make_entry({"venn-cad": Decimal("200"), "fooco": Decimal("-200")}, desc="two")
    assert validate_entries([e1, e2], FULL_REGISTRY) == []


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
