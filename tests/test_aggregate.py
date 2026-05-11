from decimal import Decimal

import pytest

from whoberi.aggregate import aggregate, check_balance
from tests.conftest import make_entry


@pytest.mark.parametrize("entries,expected", [
    ([], {}),
    (
        [make_entry({"a": Decimal("100"), "b": Decimal("-100")}),
         make_entry({"a": Decimal("50"), "b": Decimal("-50")})],
        {"a": Decimal("150"), "b": Decimal("-150")},
    ),
    (
        [make_entry({"a": Decimal("100")}), make_entry({"a": Decimal("-100")})],
        {"a": Decimal("0")},
    ),
])
def test_aggregate(entries, expected):
    assert aggregate(entries) == expected


@pytest.mark.parametrize("amounts,expected", [
    ([Decimal("100"), Decimal("-100")], Decimal("0")),
    ([Decimal("100"), Decimal("-99")], Decimal("1")),
    ([Decimal("50"), Decimal("-30"), Decimal("-20")], Decimal("0")),
    ([Decimal("0.01"), Decimal("-0.01")], Decimal("0")),
])
def test_check_balance(amounts, expected):
    combined = {str(i): a for i, a in enumerate(amounts)}
    assert check_balance(combined) == expected
