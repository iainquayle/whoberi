"""Income handler for barco — flat revenue, no HST."""
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from functools import partial

from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    return map(partial(_row_to_entry, meta=meta), rows)


def _row_to_entry(row: dict, meta: LedgerMeta) -> Entry:
    d = date.fromisoformat(row["date"].strip())
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())
    return Entry(
        date=d,
        accounts={
            "venn-cad": total,
            meta.name: total,
        },
        meta={"description": description},
    )
