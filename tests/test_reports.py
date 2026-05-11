from datetime import date
from decimal import Decimal

import pytest

from whoberi.reports import filter_by_period, report_balance, report_gst, report_payroll, report_pnl
from tests.conftest import FULL_REGISTRY, make_entry

ENTRIES = [
    # Q1: income 5250 HST-inclusive
    make_entry({"venn-cad": Decimal("5250"), "fooco": Decimal("-4646.02"), "hst-collected": Decimal("-603.98")}, d=date(2026, 1, 15)),
    # Q1: expense 157.50 HST-inclusive
    make_entry({"software": Decimal("139.38"), "hst-paid": Decimal("18.12"), "venn-cad": Decimal("-157.50")}, d=date(2026, 2, 1)),
    # Q2: income
    make_entry({"venn-cad": Decimal("2260"), "fooco": Decimal("-2000"), "hst-collected": Decimal("-260")}, d=date(2026, 4, 10)),
    # Payroll Q1
    make_entry({"salary": Decimal("5000"), "cra-tax": Decimal("-1000"), "cra-cpp": Decimal("-300"), "cra-ei": Decimal("-150"), "venn-cad": Decimal("-3550")}, d=date(2026, 1, 15)),
    # Draw Q1
    make_entry({"draws": Decimal("3000"), "venn-cad": Decimal("-3000")}, d=date(2026, 1, 20)),
]


# ─── Period filter ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("period,expected_count", [
    ("Q1 2026", 4),
    ("Q2 2026", 1),
    ("2026-01", 3),
    ("2026", 5),
])
def test_filter_by_period(period, expected_count):
    assert len(filter_by_period(ENTRIES, period)) == expected_count


def test_filter_none_returns_all():
    assert filter_by_period(ENTRIES, None) == ENTRIES


# ─── Reports ─────────────────────────────────────────────────────────────────

# _fmt in reports.py controls currency formatting; these assertions depend on it.
@pytest.mark.parametrize("report_fn,extra_args,expected_substrings", [
    (report_pnl, (FULL_REGISTRY, "Q1 2026"), ["$4,646.02", "$5,139.38"]),  # revenue, expenses
    (report_gst, ("Q1 2026",), ["$603.98", "$18.12"]),                      # collected, paid ITC
    (report_payroll, ("Q1 2026",), ["$5,000.00", "$1,000.00", "$300.00"]),  # salary, tax, cpp
])
def test_report_q1(report_fn, extra_args, expected_substrings):
    out = report_fn(ENTRIES, *extra_args)
    for s in expected_substrings:
        assert s in out


def test_balance_sheet_balances():
    out = report_balance(ENTRIES, FULL_REGISTRY)
    assert "Check (=0):" in out and "  $0.00" in out


def test_balance_sheet_date_filter():
    q1 = report_balance(ENTRIES, FULL_REGISTRY, "Q1 2026")
    all_time = report_balance(ENTRIES, FULL_REGISTRY)
    # Q1 net income is $493.36; all-time differs — assertion catches period filter regressions
    assert "$493.36" in q1
    assert "$493.36" not in all_time
