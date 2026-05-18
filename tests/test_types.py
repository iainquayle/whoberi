from decimal import Decimal

import pytest

from whoberi.aggregate import is_balanced
from tests.conftest import make_entry, make_registry


REGISTRY = make_registry(asset=["cash"], income=["sales"], expense=["meals"])


@pytest.mark.parametrize("accounts,balanced", [
    # cash sale: A(+1000) + I(+1000): 1000 - 1000 = 0
    ({"cash": Decimal("1000"), "sales": Decimal("1000")}, True),
    # expense: E(+50) + A(-50): 50 - 50 = 0
    ({"meals": Decimal("50"), "cash": Decimal("-50")}, True),
    # off by 1
    ({"cash": Decimal("100"), "sales": Decimal("99")}, False),
    # single zero
    ({"cash": Decimal("0")}, True),
])
def test_is_balanced(accounts, balanced):
    assert is_balanced(make_entry(accounts), REGISTRY) == balanced
