from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from whoberi.types import Entry, LedgerMeta


def make_entry(accounts: dict[str, Decimal]) -> Entry:
    return Entry(date=date(2026, 1, 1), accounts=accounts)


@pytest.mark.parametrize("accounts", [
    {"assets:bank": Decimal("100"), "income:foo": Decimal("-100")},
    {"a": Decimal("50"), "b": Decimal("-30"), "c": Decimal("-20")},
    {"x": Decimal("0")},
])
def test_entry_balanced(accounts):
    assert make_entry(accounts).balanced


@pytest.mark.parametrize("accounts", [
    {"assets:bank": Decimal("100"), "income:foo": Decimal("-99")},
    {"a": Decimal("0.01")},
])
def test_entry_unbalanced(accounts):
    assert not make_entry(accounts).balanced


def test_ledger_meta_defaults():
    meta = LedgerMeta(name="software", directory="expenses", path=Path("/data/expenses/software.csv"))
    assert meta.overrides == {}


def test_ledger_meta_overrides():
    meta = LedgerMeta(
        name="barco", directory="income",
        path=Path("/data/income/barco.csv"),
        overrides={"tax_applies": False},
    )
    assert meta.overrides["tax_applies"] is False
