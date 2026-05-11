"""Payroll handler — date-only input, reads salary/deductions from config."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal
from functools import partial

from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    payroll_cfg = config.get("payroll", {})
    salary = Decimal(str(payroll_cfg.get("salary", "0")))
    income_tax = Decimal(str(payroll_cfg.get("income_tax", "0")))
    cpp = Decimal(str(payroll_cfg.get("cpp", "0")))
    ei = Decimal(str(payroll_cfg.get("ei", "0")))
    net = salary - income_tax - cpp - ei
    return map(partial(_row_to_entry, salary=salary, income_tax=income_tax, cpp=cpp, ei=ei, net=net), rows)


def _row_to_entry(row: dict, salary: Decimal, income_tax: Decimal, cpp: Decimal, ei: Decimal, net: Decimal) -> Entry:
    entry_date = Date.fromisoformat(row["date"].strip())
    return Entry(
        date=entry_date,
        accounts={
            "salary": salary,
            "cra-tax": -income_tax,
            "cra-cpp": -cpp,
            "cra-ei": -ei,
            "venn-cad": -net,
        },
        meta={"description": f"Payroll {entry_date}"},
    )
