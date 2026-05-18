from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from whoberi.types import Entry


def aggregate(entries: Iterable[Entry]) -> dict[str, Decimal]:
    combined: dict[str, Decimal] = defaultdict(Decimal)
    for entry in entries:
        for account, amount in entry.accounts.items():
            combined[account] += amount
    return combined


def check_balance(combined: dict[str, Decimal]) -> Decimal:
    return sum(combined.values(), Decimal("0"))
