"""Unit tests for each reference handler."""
import importlib.util
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from whoberi.config import load_config
from whoberi.types import Entry, LedgerMeta
from tests.conftest import FIXTURES


def load_handler(rel_path: str) -> ModuleType:
    path = FIXTURES / rel_path
    spec = importlib.util.spec_from_file_location("_handler", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_meta(name: str, directory: str, overrides: dict | None = None) -> LedgerMeta:
    return LedgerMeta(
        name=name,
        directory=directory,
        path=FIXTURES / directory / f"{name}.csv",
        overrides=overrides or {},
    )


CONFIG = load_config(FIXTURES)


# --- Expense handler ---

@pytest.mark.parametrize("amount,expected_pretax,expected_hst", [
    ("157.50", Decimal("139.38"), Decimal("18.12")),
    ("113.00", Decimal("100.00"), Decimal("13.00")),
])
def test_expense_handler_splits_hst(amount, expected_pretax, expected_hst):
    handler = load_handler("expenses/handler.py")
    rows = [{"date": "2026-01-01", "description": "AWS", "amount": amount}]
    entries = list(handler.process(rows, CONFIG, make_meta("software", "expenses")))
    assert len(entries) == 1
    e = entries[0]
    assert e.balanced
    assert e.accounts["expenses:software"] == expected_pretax
    assert e.accounts["tax:hst-paid"] == expected_hst
    assert e.accounts["assets:venn-cad"] == -Decimal(amount)


# --- Income handler ---

def test_income_handler_with_tax():
    handler = load_handler("income/handler.py")
    rows = [{"date": "2026-01-15", "description": "Invoice 1", "amount": "5250.00"}]
    entries = list(handler.process(rows, CONFIG, make_meta("fooco", "income")))
    assert len(entries) == 1
    e = entries[0]
    assert e.balanced
    assert e.accounts["assets:venn-cad"] == Decimal("5250.00")
    assert "tax:hst-collected" in e.accounts
    assert e.accounts["tax:hst-collected"] < 0


def test_income_handler_no_tax():
    handler = load_handler("income/handler.py")
    rows = [{"date": "2026-02-01", "description": "Invoice 10", "amount": "3000.00"}]
    meta = make_meta("barco", "income", overrides={"tax_applies": False})
    entries = list(handler.process(rows, CONFIG, meta))
    assert len(entries) == 1
    e = entries[0]
    assert e.balanced
    assert "tax:hst-collected" not in e.accounts
    assert e.accounts["income:barco"] == -Decimal("3000.00")


# --- Payroll handler ---

def test_payroll_handler():
    handler = load_handler("payroll/handler.py")
    rows = [{"date": "2026-01-15"}]
    entries = list(handler.process(rows, CONFIG, make_meta("payroll", "payroll")))
    assert len(entries) == 1
    e = entries[0]
    assert e.balanced
    assert e.accounts["expenses:salary"] == Decimal("5000")
    assert e.accounts["liabilities:cra-tax"] == -Decimal("1000")
    assert e.accounts["liabilities:cra-cpp"] == -Decimal("300")
    assert e.accounts["liabilities:cra-ei"] == -Decimal("150")
    assert e.accounts["assets:venn-cad"] == -Decimal("3550")


# --- Draws handler ---

def test_draws_handler():
    handler = load_handler("draws/handler.py")
    rows = [{"date": "2026-01-20", "amount": "3000.00"}]
    entries = list(handler.process(rows, CONFIG, make_meta("draws", "draws")))
    assert len(entries) == 1
    e = entries[0]
    assert e.balanced
    assert e.accounts["equity:draws"] == Decimal("3000.00")
    assert e.accounts["assets:venn-cad"] == -Decimal("3000.00")


# --- Recurring expense handler ---

@pytest.mark.parametrize("rows,config_extra,expected_dates", [
    (
        [{"date": "2026-01-01", "end_date": "2026-03-01", "period": "monthly",
          "description": "AWS", "amount": "157.50"}],
        {"as_of": "2026-12-31"},
        [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)],
    ),
    (
        [{"date": "2026-01-01", "end_date": "", "period": "monthly",
          "description": "AWS", "amount": "157.50"}],
        {"as_of": "2026-03-15"},
        [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)],
    ),
])
def test_recurring_expense_handler_expands_dates(rows, config_extra, expected_dates):
    handler = load_handler("expenses/recurring/handler.py")
    config = {**CONFIG, **config_extra}
    entries = list(handler.process(iter(rows), config, make_meta("recurring", "expenses")))
    assert [e.date for e in entries] == expected_dates
    assert all(e.balanced for e in entries)
    assert all("expenses:recurring" in e.accounts for e in entries)
    assert all("tax:hst-paid" in e.accounts for e in entries)
