"""Expense handler — splits amount into pre-tax expense, HST paid, and bank debit."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal, ROUND_HALF_UP
from functools import partial

from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    return map(partial(_row_to_entry, config=config, meta=meta), rows)


def _row_to_entry(row: dict, config: dict, meta: LedgerMeta) -> Entry:
    entry_date = Date.fromisoformat(row["date"].strip())
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())
    rate = Decimal(str(config["tax"]["hst_rate"]))
    hst = (total * rate / (1 + rate)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    pretax = total - hst

    return Entry(
        date=entry_date,
        accounts={
            meta.name: pretax,
            "hst-paid": hst,
            "venn-cad": -total,
        },
        meta={"description": description},
    )
