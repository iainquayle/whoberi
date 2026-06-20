"""Expense handler — splits amount into pre-tax expense, HST paid, and bank debit."""
from collections.abc import Iterator
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import partial
from pathlib import Path

from whoberi.ledgers.books import Books
from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta, books: Books) -> Iterator[Entry]:
    return map(partial(_row_to_entry, config=config, meta=meta), rows)


def _row_to_entry(row: dict, config: dict, meta: LedgerMeta) -> Entry:
    d = date.fromisoformat(row["date"].strip())
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())
    rate = Decimal(str(config["consts"]["tax"]["hst_rate"]))
    hst = (total * rate / (1 + rate)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    pretax = total - hst

    return Entry(
        date=d,
        accounts={
            meta.name: pretax,
            "hst-paid": hst,
            "venn-cad": -total,
        },
        meta={"description": description},
    )


def _test_splits_balance_to_zero():
    cfg = {"consts": {"tax": {"hst_rate": 0.13}}}
    meta = LedgerMeta(name="software", directory="expenses", path=Path("software.csv"))
    rows = [{"date": "2026-01-15", "description": "Figma", "amount": "113.00"}]
    entries = list(process(iter(rows), cfg, meta, Books({})))
    assert len(entries) == 1
    accounts = entries[0].accounts
    assert accounts["software"] == Decimal("100.00")
    assert accounts["hst-paid"] == Decimal("13.00")
    assert accounts["venn-cad"] == Decimal("-113.00")
    assert sum(accounts.values()) == Decimal("0")
