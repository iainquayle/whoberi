import calendar
import re
from datetime import date
from decimal import Decimal

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.aggregate import aggregate, check_balance
from whoberi.types import Entry


def filter_by_period(entries: list[Entry], period: str | None) -> list[Entry]:
    if period is None:
        return entries
    start, end = _parse_period(period)
    return [e for e in entries if start <= e.date <= end]


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
    raise ValueError(f"Cannot parse period: '{period}' — valid formats: 'Q1 2026', '2026-01', '2026'")


def _month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _sum_type(combined: dict[str, Decimal], reg: AccountRegistry, t: AccountType) -> Decimal:
    return sum(
        (v for name, v in combined.items() if reg.type_of(name) == t),
        Decimal("0"),
    )


def report_pnl(entries: list[Entry], registry: AccountRegistry, period: str | None = None) -> str:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    revenue = -_sum_type(combined, registry, AccountType.INCOME)
    expenses = _sum_type(combined, registry, AccountType.EXPENSE)
    net = revenue - expenses

    lines = [f"P&L{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Revenue:   {_fmt(revenue):>12}")
    lines.append(f"  Expenses:  {_fmt(expenses):>12}")
    lines.append("─" * 40)
    lines.append(f"  Net:       {_fmt(net):>12}")
    return "\n".join(lines)


def gst_owing(combined: dict[str, Decimal]) -> tuple[Decimal, Decimal, Decimal]:
    """Return (collected, paid, owing) from a combined account dict."""
    collected = -combined.get("hst-collected", Decimal("0"))
    paid = combined.get("hst-paid", Decimal("0"))
    return collected, paid, collected - paid


def report_gst(entries: list[Entry], period: str | None = None) -> str:
    # Depends on named accounts: hst-collected, hst-paid
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    collected, paid, owing = gst_owing(combined)

    lines = [f"GST/HST{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Collected: {_fmt(collected):>12}")
    lines.append(f"  Paid (ITC):{_fmt(paid):>12}")
    lines.append("─" * 40)
    lines.append(f"  Net owing: {_fmt(owing):>12}")
    return "\n".join(lines)


def report_payroll(entries: list[Entry], period: str | None = None) -> str:
    # Depends on named accounts: salary, cra-tax, cra-cpp, cra-ei
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    salary = combined.get("salary", Decimal("0"))
    tax = -combined.get("cra-tax", Decimal("0"))
    cpp = -combined.get("cra-cpp", Decimal("0"))
    ei = -combined.get("cra-ei", Decimal("0"))

    lines = [f"Payroll{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Gross salary: {_fmt(salary):>10}")
    lines.append(f"  Income tax:   {_fmt(tax):>10}")
    lines.append(f"  CPP:          {_fmt(cpp):>10}")
    lines.append(f"  EI:           {_fmt(ei):>10}")
    return "\n".join(lines)


def report_balance(entries: list[Entry], registry: AccountRegistry, period: str | None = None) -> str:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    assets = _sum_type(combined, registry, AccountType.ASSET)
    liabilities = _sum_type(combined, registry, AccountType.LIABILITY)
    equity = _sum_type(combined, registry, AccountType.EQUITY)
    net_income = _sum_type(combined, registry, AccountType.INCOME) + _sum_type(combined, registry, AccountType.EXPENSE)

    lines = [f"Balance Sheet{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Assets:      {_fmt(assets):>10}")
    lines.append(f"  Liabilities: {_fmt(liabilities):>10}")
    lines.append(f"  Equity:      {_fmt(equity):>10}")
    lines.append(f"  Net income:  {_fmt(net_income):>10}")
    lines.append("─" * 40)
    check = check_balance(combined)
    lines.append(f"  Check (=0):  {_fmt(check):>10}")
    return "\n".join(lines)


def _fmt(amount: Decimal) -> str:
    return f"${amount:,.2f}"
