"""Income handler — splits HST-inclusive payment into revenue, HST collected, and bank credit."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal
from functools import partial

from whoberi.tax import split_hst
from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    tax_applies = meta.overrides.get("tax_applies", True)
    return map(partial(_row_to_entry, config=config, tax_applies=tax_applies, meta=meta), rows)


def _row_to_entry(row: dict, config: dict, tax_applies: bool, meta: LedgerMeta) -> Entry:
    entry_date = Date.fromisoformat(row["date"].strip())
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())

    if tax_applies:
        revenue, hst = split_hst(total, config)
        accounts = {
            "assets:venn-cad": total,
            f"income:{meta.name}": -revenue,
            "tax:hst-collected": -hst,
        }
    else:
        accounts = {
            "assets:venn-cad": total,
            f"income:{meta.name}": -total,
        }

    return Entry(date=entry_date, accounts=accounts, meta={"description": description})
