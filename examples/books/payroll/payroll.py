"""Payroll handler — date-only input, reads salary/deductions from config."""
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from functools import partial

from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    payroll_cfg = config["consts"]["payroll"]
    salary = Decimal(str(payroll_cfg["salary"]))
    income_tax = Decimal(str(payroll_cfg["income_tax"]))
    cpp = Decimal(str(payroll_cfg["cpp"]))
    ei = Decimal(str(payroll_cfg["ei"]))
    net = salary - income_tax - cpp - ei
    return map(partial(_row_to_entry, salary=salary, income_tax=income_tax, cpp=cpp, ei=ei, net=net), rows)


def _row_to_entry(row: dict, salary: Decimal, income_tax: Decimal, cpp: Decimal, ei: Decimal, net: Decimal) -> Entry:
    d = date.fromisoformat(row["date"].strip())
    return Entry(
        date=d,
        accounts={
            "salary": salary,
            "cra-tax": income_tax,
            "cra-cpp": cpp,
            "cra-ei": ei,
            "venn-cad": -net,
        },
        meta={"description": f"Payroll {d}"},
    )
