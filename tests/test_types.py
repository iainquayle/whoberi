from decimal import Decimal

import pytest

from tests.conftest import make_entry


@pytest.mark.parametrize("accounts", [
    {"bank": Decimal("100"), "revenue": Decimal("-100")},
    {"a": Decimal("50"), "b": Decimal("-30"), "c": Decimal("-20")},
    {"x": Decimal("0")},
])
def test_entry_balanced(accounts):
    assert make_entry(accounts).balanced


@pytest.mark.parametrize("accounts", [
    {"bank": Decimal("100"), "revenue": Decimal("-99")},
    {"a": Decimal("0.01")},
])
def test_entry_unbalanced(accounts):
    assert not make_entry(accounts).balanced
