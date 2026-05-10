"""Income handler — splits HST-inclusive payment into revenue, HST collected, and bank credit."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal, ROUND_HALF_UP
from functools import partial

from whoberi.types import Entry, LedgerMeta

_DEFAULT_HST = Decimal("0.13")
_CENT = Decimal("0.01")


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    hst_rate = Decimal(str(config.get("tax", {}).get("hst_rate", _DEFAULT_HST)))
    tax_applies = meta.overrides.get("tax_applies", True)
    return map(partial(_row_to_entry, hst_rate=hst_rate, tax_applies=tax_applies, meta=meta), rows)


def _row_to_entry(row: dict, hst_rate: Decimal, tax_applies: bool, meta: LedgerMeta) -> Entry:
    entry_date = Date.fromisoformat(row["date"].strip())
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())

    if tax_applies:
        hst = (total * hst_rate / (1 + hst_rate)).quantize(_CENT, ROUND_HALF_UP)
        revenue = total - hst
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
