import calendar
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


def _parse_period(period: str) -> tuple[date, date]:
    period = period.upper()

    if period.startswith("Q") and period[1:].isdigit():
        q = int(period[1:])
        if q not in (1, 2, 3, 4):
            raise ValueError(f"Invalid quarter: {period}")
        year = date.today().year
        month_start = (q - 1) * 3 + 1
        month_end = q * 3
        return date(year, month_start, 1), _month_end(year, month_end)

    parts = period.split()
    if len(parts) == 2:
        if parts[0].startswith("Q"):
            q, year = int(parts[0][1:]), int(parts[1])
        else:
            year, q = int(parts[0]), int(parts[1][1:])
        month_start = (q - 1) * 3 + 1
        month_end = q * 3
        return date(year, month_start, 1), _month_end(year, month_end)

    if len(period) == 7 and period[4] == "-":
        year, month = int(period[:4]), int(period[5:])
        return date(year, month, 1), _month_end(year, month)

    if len(period) == 4 and period.isdigit():
        year = int(period)
        return date(year, 1, 1), date(year, 12, 31)

    raise ValueError(f"Cannot parse period: '{period}'")


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


def report_gst(entries: list[Entry], registry: AccountRegistry, period: str | None = None) -> str:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    collected = -combined.get("hst-collected", Decimal("0"))
    paid = combined.get("hst-paid", Decimal("0"))
    owing = collected - paid

    lines = [f"GST/HST{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Collected: {_fmt(collected):>12}")
    lines.append(f"  Paid (ITC):{_fmt(paid):>12}")
    lines.append("─" * 40)
    lines.append(f"  Net owing: {_fmt(owing):>12}")
    return "\n".join(lines)


def report_payroll(entries: list[Entry], registry: AccountRegistry, period: str | None = None) -> str:
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
