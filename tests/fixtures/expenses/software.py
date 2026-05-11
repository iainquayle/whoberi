"""Expense handler — splits amount into pre-tax expense, HST paid, and bank debit."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal
from functools import partial

from whoberi.tax import split_hst
from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    return map(partial(_row_to_entry, config=config, meta=meta), rows)


def _row_to_entry(row: dict, config: dict, meta: LedgerMeta) -> Entry:
    entry_date = Date.fromisoformat(row["date"].strip())
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())
    pretax, hst = split_hst(total, config)

    return Entry(
        date=entry_date,
        accounts={
            f"expenses:{meta.name}": pretax,
            "tax:hst-paid": hst,
            "assets:venn-cad": -total,
        },
        meta={"description": description},
    )
