"""Recurring expense handler — expands date ranges into individual entries."""
from collections.abc import Iterator
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import partial
from itertools import chain

from whoberi.dateutil import expand_dates
from whoberi.ledgers.books import Books
from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta, books: Books) -> Iterator[Entry]:
    as_of_str = config.get("as_of")
    as_of = date.fromisoformat(as_of_str) if as_of_str else date.today()
    return chain.from_iterable(map(partial(_expand_row, config=config, as_of=as_of, meta=meta), rows))


def _expand_row(row: dict, config: dict, as_of: date, meta: LedgerMeta) -> Iterator[Entry]:
    start = date.fromisoformat(row["date"].strip())
    end_str = row.get("end-date", "").strip()
    end = date.fromisoformat(end_str) if end_str else None
    period = row["period"].strip()
    description = row["description"].strip()
    total = Decimal(row["amount"].strip())
    rate = Decimal(str(config["consts"]["tax"]["hst_rate"]))
    hst = (total * rate / (1 + rate)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    pretax = total - hst

    return map(
        lambda d: Entry(
            date=d,
            accounts={
                meta.name: pretax,
                "hst-paid": hst,
                "venn-cad": -total,
            },
            meta={"description": description},
        ),
        expand_dates(start, period, as_of, end),
    )
