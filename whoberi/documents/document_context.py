from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from whoberi.accounts import AccountRegistry
from whoberi.aggregate import aggregate
from whoberi.money import fmt_money
from whoberi.period import filter_as_of, filter_by_period
from whoberi.types import Entry


@dataclass(frozen=True)
class DocumentContext:
    """What a generator sees: a reporter's aggregates plus the entries behind them."""
    entries: tuple[Entry, ...]             # within period (or all if period is None)
    cumulative_entries: tuple[Entry, ...]  # date <= period end (or all if period is None)
    combined: dict[str, Decimal]           # aggregate of `entries`
    registry: AccountRegistry
    config: dict
    period: str | None

    def by_ledger(self) -> dict[str, tuple[Entry, ...]]:
        """Group `entries` by their 'ledger' meta tag ('income/fooco'). Untagged entries raise."""
        grouped: dict[str, list[Entry]] = defaultdict(list)
        for entry in self.entries:
            grouped[entry.meta["ledger"]].append(entry)
        return {key: tuple(group) for key, group in grouped.items()}

    def by_account(self, name: str) -> tuple[Entry, ...]:
        return tuple(e for e in self.entries if name in e.accounts)

    def fmt(self, amount: Decimal) -> str:
        return fmt_money(amount)


def make_document_context(
    entries: list[Entry], registry: AccountRegistry, config: dict, period: str | None
) -> DocumentContext:
    # entries stays a list because both filters are applied to the same source.
    period_entries = tuple(filter_by_period(entries, period))
    return DocumentContext(
        entries=period_entries,
        cumulative_entries=tuple(filter_as_of(entries, period)),
        combined=aggregate(period_entries),
        registry=registry,
        config=config,
        period=period,
    )
