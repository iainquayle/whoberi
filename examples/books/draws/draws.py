"""Draws handler — date + amount, equity draw against bank account."""
from collections.abc import Iterator
from datetime import date
from decimal import Decimal

from whoberi.ledgers.books import Books
from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta, books: Books) -> Iterator[Entry]:
    return map(_row_to_entry, rows)


def _row_to_entry(row: dict) -> Entry:
    d = date.fromisoformat(row["date"].strip())
    amount = Decimal(row["amount"].strip())
    return Entry(
        date=d,
        accounts={
            "draws": -amount,
            "venn-cad": -amount,
        },
        meta={"description": "Shareholder draw"},
    )
