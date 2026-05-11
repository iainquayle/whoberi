import calendar
import re
from datetime import date
from decimal import Decimal

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.aggregate import aggregate, check_balance
from whoberi.report_context import ReportContext
from whoberi.report_discovery import ReportDef
from whoberi.types import Entry


def filter_by_period(entries: list[Entry], period: str | None) -> list[Entry]:
    if period is None:
        return entries
    start, end = _parse_period(period)
    return [e for e in entries if start <= e.date <= end]


def make_context(
    entries: list[Entry], registry: AccountRegistry, period: str | None
) -> ReportContext:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)
    return ReportContext(combined=combined, registry=registry, period=period)


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


def report_pnl(ctx: ReportContext) -> str:
    revenue = -ctx.sum_type(AccountType.INCOME)
    expenses = ctx.sum_type(AccountType.EXPENSE)
    net = revenue - expenses
    return ctx.render(
        [
            ("Revenue", revenue),
            ("Expenses", expenses),
            None,
            ("Net", net),
        ],
        title=f"P&L{ctx.period_suffix}",
    )


def report_balance(ctx: ReportContext) -> str:
    assets = ctx.sum_type(AccountType.ASSET)
    liabilities = ctx.sum_type(AccountType.LIABILITY)
    equity = ctx.sum_type(AccountType.EQUITY)
    net_income = ctx.sum_type(AccountType.INCOME) + ctx.sum_type(AccountType.EXPENSE)
    check = check_balance(ctx.combined)
    return ctx.render(
        [
            ("Assets", assets),
            ("Liabilities", liabilities),
            ("Equity", equity),
            ("Net income", net_income),
            None,
            ("Check (=0)", check),
        ],
        title=f"Balance Sheet{ctx.period_suffix}",
    )


def report_accounts(ctx: ReportContext) -> str:
    lines = [f"Accounts{ctx.period_suffix}", "─" * 40]
    for t in AccountType:
        accounts = {
            name: val
            for name, val in ctx.combined.items()
            if ctx.registry.type_of(name) == t
        }
        if not accounts:
            continue
        lines.append(f"  [{t.value}]")
        width = max(len(n) for n in accounts)
        for name in sorted(accounts):
            lines.append(f"    {name:<{width}}  {ctx.fmt(accounts[name]):>12}")
    return "\n".join(lines)


BUILTIN_REPORTS: dict[str, ReportDef] = {
    name: ReportDef(name=name, description=desc, fn=fn, source="built-in")
    for name, desc, fn in [
        ("accounts", "All accounts by category", report_accounts),
        ("balance", "Balance sheet", report_balance),
        ("pnl", "Profit & Loss", report_pnl),
    ]
}
