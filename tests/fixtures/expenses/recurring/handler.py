"""Recurring expense handler — expands date ranges into individual entries."""
from collections.abc import Iterator
from datetime import date as Date
from decimal import Decimal, ROUND_HALF_UP
from functools import partial
from itertools import chain

from whoberi.dateutil import expand_dates
from whoberi.types import Entry, LedgerMeta

_DEFAULT_HST = Decimal("0.13")
_CENT = Decimal("0.01")


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    hst_rate = Decimal(str(config.get("tax", {}).get("hst_rate", _DEFAULT_HST)))
    as_of_str = config.get("as_of")
    as_of = Date.fromisoformat(as_of_str) if as_of_str else Date.today()
    return chain.from_iterable(map(partial(_expand_row, hst_rate=hst_rate, as_of=as_of, meta=meta), rows))


def _expand_row(row: dict, hst_rate: Decimal, as_of: Date, meta: LedgerMeta) -> Iterator[Entry]:
    start = Date.fromisoformat(row["date"].strip())
    end_str = row.get("end_date", "").strip()
    end = Date.fromisoformat(end_str) if end_str else None
    period = row["period"].strip()
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())

    hst = (total * hst_rate / (1 + hst_rate)).quantize(_CENT, ROUND_HALF_UP)
    pretax = total - hst

    return map(
        lambda d: Entry(
            date=d,
            accounts={
                f"expenses:{meta.name}": pretax,
                "tax:hst-paid": hst,
                "assets:venn-cad": -total,
            },
            meta={"description": description},
        ),
        expand_dates(start, period, as_of, end),
    )
