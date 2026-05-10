"""Expense handler — splits amount into pre-tax expense, HST paid, and bank debit."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal, ROUND_HALF_UP
from functools import partial

from whoberi.types import Entry, LedgerMeta

_DEFAULT_HST = Decimal("0.13")
_CENT = Decimal("0.01")


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    hst_rate = Decimal(str(config.get("tax", {}).get("hst_rate", _DEFAULT_HST)))
    return map(partial(_row_to_entry, hst_rate=hst_rate, meta=meta), rows)


def _row_to_entry(row: dict, hst_rate: Decimal, meta: LedgerMeta) -> Entry:
    entry_date = Date.fromisoformat(row["date"].strip())
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())

    # Back-calculate pre-tax from HST-inclusive total
    hst = (total * hst_rate / (1 + hst_rate)).quantize(_CENT, ROUND_HALF_UP)
    pretax = total - hst

    return Entry(
        date=entry_date,
        accounts={
            f"expenses:{meta.name}": pretax,
            "tax:hst-paid": hst,
            "assets:venn-cad": -total,
        },
        meta={"description": description},
    )
