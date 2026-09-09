"""DocumentContext construction and grouping helpers."""
from datetime import date
from decimal import Decimal

import pytest

from whoberi.documents.document_context import make_document_context
from tests.conftest import FULL_REGISTRY, make_entry

CONFIG = {"consts": {"clients": {"fooco": {"name": "Fooco Industries Ltd."}}}}


def _tagged(ledger: str, d: date, accounts: dict[str, Decimal]):
    entry = make_entry(accounts, d=d)
    entry.meta["ledger"] = ledger
    return entry


ENTRIES = [
    _tagged("income/fooco", date(2026, 1, 15), {"venn-cad": Decimal("100"), "fooco": Decimal("100")}),
    _tagged("income/barco", date(2026, 2, 1), {"venn-cad": Decimal("50"), "barco": Decimal("50")}),
    _tagged("income/fooco", date(2026, 4, 10), {"venn-cad": Decimal("20"), "fooco": Decimal("20")}),
]


def _ctx(period):
    return make_document_context(ENTRIES, FULL_REGISTRY, CONFIG, period)


@pytest.mark.parametrize("period,entries,cumulative", [
    (None, 3, 3),
    ("Q1 2026", 2, 2),
    ("Q2 2026", 1, 3),
    ("2026-01", 1, 1),
])
def test_period_filtering(period, entries, cumulative):
    ctx = _ctx(period)
    assert len(ctx.entries) == entries
    assert len(ctx.cumulative_entries) == cumulative


def test_combined_aggregates_period_entries_only():
    assert _ctx("Q1 2026").combined["venn-cad"] == Decimal("150")


def test_by_ledger_groups_by_tag():
    grouped = _ctx(None).by_ledger()
    assert set(grouped) == {"income/fooco", "income/barco"}
    assert len(grouped["income/fooco"]) == 2


def test_by_ledger_respects_period():
    assert set(_ctx("Q2 2026").by_ledger()) == {"income/fooco"}


def test_by_ledger_untagged_entry_raises():
    ctx = make_document_context([make_entry({"venn-cad": Decimal("1")})], FULL_REGISTRY, CONFIG, None)
    with pytest.raises(KeyError, match="ledger"):
        ctx.by_ledger()


def test_by_account():
    assert len(_ctx(None).by_account("fooco")) == 2
    assert _ctx(None).by_account("nothing-here") == ()


def test_fmt_uses_accountant_formatting():
    assert _ctx(None).fmt(Decimal("-1234.5")) == "$(1,234.50)"
