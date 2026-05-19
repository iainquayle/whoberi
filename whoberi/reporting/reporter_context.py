from dataclasses import dataclass
from decimal import Decimal

from whoberi.accounts import AccountRegistry, AccountType


def fmt_money(amount: Decimal) -> str:
    if amount < 0:
        return f"$({-amount:,.2f})"
    return f"${amount:,.2f}"


@dataclass(frozen=True)
class ReporterContext:
    combined: dict[str, Decimal]      # entries within period (or all if period is None)
    cumulative: dict[str, Decimal]    # entries with date <= period end (or all if period is None)
    registry: AccountRegistry
    period: str | None

    @property
    def period_suffix(self) -> str:
        return f" — {self.period}" if self.period else ""

    def sum_type(self, t: AccountType) -> Decimal:
        return sum(self.period_by_type(t).values(), Decimal("0"))

    def sum_type_as_of(self, t: AccountType) -> Decimal:
        return sum(self.cumulative_by_type(t).values(), Decimal("0"))

    def period_by_type(self, t: AccountType) -> dict[str, Decimal]:
        return {n: v for n, v in self.combined.items() if self.registry.type_of(n) == t}

    def cumulative_by_type(self, t: AccountType) -> dict[str, Decimal]:
        return {n: v for n, v in self.cumulative.items() if self.registry.type_of(n) == t}

    def fmt(self, amount: Decimal) -> str:
        return fmt_money(amount)

    def render(self, rows: list[tuple[str, Decimal] | None], title: str) -> str:
        label_width = max(
            (len(r[0]) for r in rows if r is not None),
            default=10,
        )
        lines = [title, "─" * 40]
        for row in rows:
            if row is None:
                lines.append("─" * 40)
            else:
                label, amount = row
                lines.append(f"  {label:<{label_width}}  {self.fmt(amount):>12}")
        return "\n".join(lines)
