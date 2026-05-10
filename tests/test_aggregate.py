from datetime import date
from decimal import Decimal

import pytest

from whoberi.aggregate import aggregate, check_balance
from whoberi.types import Entry


def make_entry(accounts: dict[str, Decimal]) -> Entry:
    return Entry(date=date(2026, 1, 1), accounts=accounts)


def test_aggregate_sums_accounts():
    entries = [
        make_entry({"a": Decimal("100"), "b": Decimal("-100")}),
        make_entry({"a": Decimal("50"), "b": Decimal("-50")}),
    ]
    result = aggregate(entries)
    assert result["a"] == Decimal("150")
    assert result["b"] == Decimal("-150")


def test_aggregate_empty():
    assert aggregate([]) == {}


def test_check_balance_zero():
    combined = {"a": Decimal("100"), "b": Decimal("-100")}
    assert check_balance(combined) == Decimal("0")


def test_check_balance_nonzero():
    combined = {"a": Decimal("100"), "b": Decimal("-99")}
    assert check_balance(combined) == Decimal("1")


@pytest.mark.parametrize("amounts,expected", [
    ([Decimal("50"), Decimal("-30"), Decimal("-20")], Decimal("0")),
    ([Decimal("0.01"), Decimal("-0.01")], Decimal("0")),
])
def test_check_balance_parametrized(amounts, expected):
    combined = {str(i): a for i, a in enumerate(amounts)}
    assert check_balance(combined) == expected
