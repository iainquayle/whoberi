from dataclasses import dataclass
from decimal import Decimal

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.types import Entry


@dataclass(frozen=True)
class ReportContext:
    entries: list[Entry]
    combined: dict[str, Decimal]
    registry: AccountRegistry
    period: str | None

    @property
    def period_suffix(self) -> str:
        return f" — {self.period}" if self.period else ""

    def sum_type(self, t: AccountType) -> Decimal:
        return sum(
            (v for name, v in self.combined.items() if self.registry.type_of(name) == t),
            Decimal("0"),
        )

    def fmt(self, amount: Decimal) -> str:
        return f"${amount:,.2f}"

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
