from datetime import date
from decimal import Decimal

import pytest

from whoberi.reporting.reports import filter_as_of, filter_by_period, make_context, report_accounts, report_balance, report_pnl
from tests.conftest import FULL_REGISTRY, SAMPLE_ENTRIES, make_entry


# ─── Period filter ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("period,expected_count", [
    ("Q1 2026", 4),
    ("Q2 2026", 1),
    ("2026-01", 3),
    ("2026", 5),
])
def test_filter_by_period(period, expected_count):
    assert len(list(filter_by_period(SAMPLE_ENTRIES, period))) == expected_count


def test_filter_none_returns_all():
    assert list(filter_by_period(SAMPLE_ENTRIES, None)) == SAMPLE_ENTRIES


def test_filter_as_of():
    assert len(list(filter_as_of(SAMPLE_ENTRIES, "Q1 2026"))) == 4


def test_invalid_period_raises():
    with pytest.raises(ValueError, match="Cannot parse period"):
        list(filter_by_period(SAMPLE_ENTRIES, "not-a-period"))


# ─── Built-in reports ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("report_fn,expected_substrings", [
    (report_pnl, ["$4,646.02", "$5,139.38"]),
    (report_balance, ["$493.36", "$0.00"]),
    (report_accounts, ["[income]", "[expense]", "fooco", "salary"]),
])
def test_report_q1(report_fn, expected_substrings):
    ctx = make_context(SAMPLE_ENTRIES, FULL_REGISTRY, "Q1 2026")
    out = report_fn(ctx)
    for s in expected_substrings:
        assert s in out


def test_balance_sheet_balances():
    ctx = make_context(SAMPLE_ENTRIES, FULL_REGISTRY, None)
    out = report_balance(ctx)
    assert "Check (=0)" in out and "$0.00" in out


def test_balance_sheet_date_filter():
    q1 = report_balance(make_context(SAMPLE_ENTRIES, FULL_REGISTRY, "Q1 2026"))
    all_time = report_balance(make_context(SAMPLE_ENTRIES, FULL_REGISTRY, None))
    assert "$493.36" in q1
    assert "$493.36" not in all_time


def test_balance_uses_cumulative_not_period_filter():
    pre_period = make_entry({"venn-cad": Decimal("1000"), "fooco": Decimal("-1000")}, d=date(2025, 6, 1))
    in_period = make_entry({"venn-cad": Decimal("500"), "fooco": Decimal("-500")}, d=date(2026, 1, 15))
    entries = [pre_period, in_period]

    ctx = make_context(entries, FULL_REGISTRY, "Q1 2026")
    balance = report_balance(ctx)
    pnl = report_pnl(ctx)

    # balance uses cumulative: assets reflect both entries
    assert "$1,500.00" in balance
    # pnl uses period filter: revenue reflects only in-period entry
    assert "$500.00" in pnl
    assert "$1,500.00" not in pnl
