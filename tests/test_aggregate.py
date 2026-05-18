from decimal import Decimal

import pytest

from whoberi.aggregate import aggregate, check_balance
from tests.conftest import make_entry, make_registry


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


# Type-weighted: asset/expense +1, liability/equity/income -1.
REGISTRY = make_registry(
    asset=["cash"], income=["sales"], liability=["tax"], expense=["meals"], equity=["draws"]
)


@pytest.mark.parametrize("combined,expected", [
    # cash sale: cash(A,+)+1000 + sales(I,-)+1000 = 0
    ({"cash": Decimal("1000"), "sales": Decimal("1000")}, Decimal("0")),
    # expense paid in cash: meals(E,+)+50 + cash(A,+)(-50) = 0
    ({"meals": Decimal("50"), "cash": Decimal("-50")}, Decimal("0")),
    # liability increase paired with asset increase: cash(A,+)100 + tax(L,-)100 = 0
    ({"cash": Decimal("100"), "tax": Decimal("100")}, Decimal("0")),
    # draw (both decreases): draws(Eq,-)(-3000) + cash(A,+)(-3000) = 0
    ({"draws": Decimal("-3000"), "cash": Decimal("-3000")}, Decimal("0")),
    # off
    ({"cash": Decimal("100"), "sales": Decimal("50")}, Decimal("50")),
    ({"sales": Decimal("100")}, Decimal("-100")),
])
def test_check_balance(combined, expected):
    assert check_balance(combined, REGISTRY) == expected
