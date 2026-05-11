"""Travel expense handler."""
from collections.abc import Iterator

from whoberi.types import Entry, LedgerMeta


def process(rows: Iterator[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]:
    return iter(())
