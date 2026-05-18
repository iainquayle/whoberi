from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from whoberi.accounts import AccountRegistry
from whoberi.types import Entry


def aggregate(entries: Iterable[Entry]) -> dict[str, Decimal]:
    combined: dict[str, Decimal] = defaultdict(Decimal)
    for entry in entries:
        for account, amount in entry.accounts.items():
            combined[account] += amount
    return combined


def check_balance(amounts: dict[str, Decimal], registry: AccountRegistry) -> Decimal:
    """Type-weighted sum: asset/expense add, liability/equity/income subtract. Zero == balanced."""
    return sum(
        (amount * registry.sign_of(name) for name, amount in amounts.items()),
        Decimal("0"),
    )


def is_balanced(entry: Entry, registry: AccountRegistry) -> bool:
    return check_balance(entry.accounts, registry) == 0
