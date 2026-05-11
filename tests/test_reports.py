from datetime import date
from decimal import Decimal

import pytest

from whoberi.reports import filter_by_period, report_balance, report_gst, report_payroll, report_pnl
from tests.conftest import make_entry

ENTRIES = [
    # Q1: income 5250 HST-inclusive
    make_entry({"assets:venn-cad": Decimal("5250"), "income:fooco": Decimal("-4646.02"), "tax:hst-collected": Decimal("-603.98")}, d=date(2026, 1, 15)),
    # Q1: expense 157.50 HST-inclusive
    make_entry({"expenses:software": Decimal("139.38"), "tax:hst-paid": Decimal("18.12"), "assets:venn-cad": Decimal("-157.50")}, d=date(2026, 2, 1)),
    # Q2: income
    make_entry({"assets:venn-cad": Decimal("2260"), "income:fooco": Decimal("-2000"), "tax:hst-collected": Decimal("-260")}, d=date(2026, 4, 10)),
    # Payroll Q1
    make_entry({"expenses:salary": Decimal("5000"), "liabilities:cra-tax": Decimal("-1000"), "liabilities:cra-cpp": Decimal("-300"), "liabilities:cra-ei": Decimal("-150"), "assets:venn-cad": Decimal("-3550")}, d=date(2026, 1, 15)),
    # Draw Q1
    make_entry({"equity:draws": Decimal("3000"), "assets:venn-cad": Decimal("-3000")}, d=date(2026, 1, 20)),
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

def test_pnl_q1():
    out = report_pnl(ENTRIES, "Q1 2026")
    assert "$4,646.02" in out   # revenue
    assert "$5,139.38" in out   # expenses (salary 5000 + software 139.38)


def test_pnl_all():
    out = report_pnl(ENTRIES)
    assert "Revenue" in out and "Expenses" in out and "Net" in out


def test_gst_q1():
    out = report_gst(ENTRIES, "Q1 2026")
    assert "$603.98" in out    # collected
    assert "$18.12" in out     # paid


def test_payroll_report():
    out = report_payroll(ENTRIES, "Q1 2026")
    assert "$5,000.00" in out   # salary
    assert "$1,000.00" in out   # tax
    assert "$300.00" in out     # cpp


def test_balance_sheet_balances():
    assert "$0.00" in report_balance(ENTRIES)


def test_balance_sheet_date_filter():
    assert report_balance(ENTRIES, "Q1 2026") != report_balance(ENTRIES)
