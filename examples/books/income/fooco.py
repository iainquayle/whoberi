"""Income handler for fooco — HST-inclusive invoice, tax always applies."""
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
    rate = Decimal(str(config["consts"]["tax"]["hst_rate"]))
    hst = (total * rate / (1 + rate)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    revenue = total - hst
    return Entry(
        date=entry_date,
        accounts={
            "venn-cad": total,
            meta.name: revenue,
            "hst-collected": hst,
        },
        meta={"description": description},
    )
