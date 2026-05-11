"""Draws handler — date + amount, equity draw against bank account."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal

from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    return map(_row_to_entry, rows)


def _row_to_entry(row: dict) -> Entry:
    entry_date = Date.fromisoformat(row["date"].strip())
    amount = Decimal(row["amount"].strip())
    return Entry(
        date=entry_date,
        accounts={
            "equity:draws": amount,
            "assets:venn-cad": -amount,
        },
        meta={"description": "Shareholder draw"},
    )
