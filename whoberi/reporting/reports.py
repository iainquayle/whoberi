import calendar
import re
from collections.abc import Iterable, Iterator
from datetime import date
from decimal import Decimal

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.aggregate import aggregate
from whoberi.reporting.reporter_context import ReporterContext, fmt_money
from whoberi.reporting.reporter_discovery import ReporterDef
from whoberi.types import Entry


Section = tuple[str, list[tuple[str, Decimal]], str, Decimal]   # header, rows, total-label, total


def filter_by_period(entries: Iterable[Entry], period: str | None) -> Iterator[Entry]:
    if period is None:
        return iter(entries)
    start, end = _parse_period(period)
    return (e for e in entries if start <= e.date <= end)


def filter_as_of(entries: Iterable[Entry], period: str | None) -> Iterator[Entry]:
    if period is None:
        return iter(entries)
    _, end = _parse_period(period)
    return (e for e in entries if e.date <= end)


def make_context(
    entries: list[Entry], registry: AccountRegistry, period: str | None
) -> ReporterContext:
    # entries stays a list because both filters are applied to the same source.
    return ReporterContext(
        combined=aggregate(filter_by_period(entries, period)),
        cumulative=aggregate(filter_as_of(entries, period)),
        registry=registry,
        period=period,
    )


def _quarter(m: re.Match) -> tuple[date, date]:
    q, year = int(m.group(1)), int(m.group(2))
    month_start = (q - 1) * 3 + 1
    return date(year, month_start, 1), _month_end(year, month_start + 2)


def _month_from_match(m: re.Match) -> tuple[date, date]:
    year, month = int(m.group(1)), int(m.group(2))
    return date(year, month, 1), _month_end(year, month)


def _year_from_match(m: re.Match) -> tuple[date, date]:
    year = int(m.group(1))
    return date(year, 1, 1), date(year, 12, 31)


_PERIOD_PATTERNS = [
    (re.compile(r"^Q([1-4]) (\d{4})$"), _quarter),
    (re.compile(r"^(\d{4})-(\d{2})$"), _month_from_match),
    (re.compile(r"^(\d{4})$"), _year_from_match),
]


def _parse_period(period: str) -> tuple[date, date]:
    s = period.strip().upper()
    for pattern, builder in _PERIOD_PATTERNS:
        m = pattern.match(s)
        if m:
            return builder(m)
    raise ValueError(
        f"Cannot parse period: '{period}' — valid formats: 'Q1 2026', '2026-01', '2026'"
    )


def _month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _period_end_str(period: str | None) -> str | None:
    if period is None:
        return None
    return _parse_period(period)[1].isoformat()


def _render_statement(title: str, sections: list[Section], final: tuple[str, Decimal]) -> str:
    candidates: list[str] = []
    for _, rows, total_label, _ in sections:
        candidates.extend(n for n, _ in rows)
        candidates.append(total_label)
    candidates.append(final[0])
    label_width = max((len(c) for c in candidates), default=10)
    divider_width = label_width + 20  # 4 indent + label + 2 gap + 14 amount

    lines = [title, "─" * divider_width]
    for i, (header, rows, total_label, total) in enumerate(sections):
        if i > 0:
            lines.append("")
        lines.append(f"  {header}")
        for name, amount in rows:
            lines.append(f"    {name:<{label_width}}  {fmt_money(amount):>14}")
        lines.append(f"    {total_label:<{label_width}}  {fmt_money(total):>14}")
    lines.append("─" * divider_width)
    final_label, final_amount = final
    lines.append(f"  {final_label:<{label_width + 2}}  {fmt_money(final_amount):>14}")
    return "\n".join(lines)


def report_pnl(ctx: ReporterContext) -> str:
    revenue_accounts = ctx.period_by_type(AccountType.INCOME)
    expense_accounts = ctx.period_by_type(AccountType.EXPENSE)
    revenue_total = sum(revenue_accounts.values(), Decimal("0"))
    expenses_total = sum(expense_accounts.values(), Decimal("0"))
    net = revenue_total - expenses_total

    end = _period_end_str(ctx.period)
    title = f"Income Statement — for the period ended {end}" if end else "Income Statement — for all entries"

    sections: list[Section] = [
        ("REVENUE", sorted(revenue_accounts.items()), "Total revenue", revenue_total),
        ("EXPENSES", sorted(expense_accounts.items()), "Total expenses", expenses_total),
    ]
    return _render_statement(title, sections, ("Net income (loss)", net))


def report_balance(ctx: ReporterContext) -> str:
    assets = ctx.cumulative_by_type(AccountType.ASSET)
    liabilities = ctx.cumulative_by_type(AccountType.LIABILITY)
    equity = ctx.cumulative_by_type(AccountType.EQUITY)
    income_total = sum(ctx.cumulative_by_type(AccountType.INCOME).values(), Decimal("0"))
    expense_total = sum(ctx.cumulative_by_type(AccountType.EXPENSE).values(), Decimal("0"))
    current_earnings = income_total - expense_total

    total_assets = sum(assets.values(), Decimal("0"))
    total_liabilities = sum(liabilities.values(), Decimal("0"))
    total_equity = sum(equity.values(), Decimal("0")) + current_earnings

    equity_rows = sorted(equity.items()) + [("Current period earnings", current_earnings)]

    end = _period_end_str(ctx.period)
    title = f"Balance Sheet — as at {end}" if end else "Balance Sheet"

    sections: list[Section] = [
        ("ASSETS", sorted(assets.items()), "Total assets", total_assets),
        ("LIABILITIES", sorted(liabilities.items()), "Total liabilities", total_liabilities),
        ("EQUITY", equity_rows, "Total equity", total_equity),
    ]
    return _render_statement(
        title, sections, ("Total liabilities & equity", total_liabilities + total_equity)
    )


def report_accounts(ctx: ReporterContext) -> str:
    lines = [f"Trial Balance{ctx.period_suffix}", "─" * 40]
    for t in AccountType:
        accounts = ctx.period_by_type(t)
        if not accounts:
            continue
        lines.append(f"  [{t.value}]")
        width = max(len(n) for n in accounts)
        for name in sorted(accounts):
            lines.append(f"    {name:<{width}}  {fmt_money(accounts[name]):>14}")
    return "\n".join(lines)


BUILTIN_REPORTERS: dict[str, ReporterDef] = {
    name: ReporterDef(name=name, description=desc, fn=fn, source="built-in")
    for name, desc, fn in [
        ("accounts", "Trial balance — accounts grouped by type, with balances", report_accounts),
        ("balance", "Balance sheet", report_balance),
        ("pnl", "Income statement (profit & loss)", report_pnl),
    ]
}
