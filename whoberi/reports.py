import calendar
from datetime import date
from decimal import Decimal

from whoberi.aggregate import aggregate, check_balance
from whoberi.types import Entry


def filter_by_period(entries: list[Entry], period: str | None) -> list[Entry]:
    """Filter entries by period string: Q1-Q4, YYYY-MM, or YYYY."""
    if period is None:
        return entries

    start, end = _parse_period(period)
    return [e for e in entries if start <= e.date <= end]


def _parse_period(period: str) -> tuple[date, date]:
    period = period.upper()

    # Quarter: Q1-Q4 (uses current year from entries is not available, so use today's year)
    if period.startswith("Q") and period[1:].isdigit():
        q = int(period[1:])
        if q not in (1, 2, 3, 4):
            raise ValueError(f"Invalid quarter: {period}")
        year = date.today().year
        month_start = (q - 1) * 3 + 1
        month_end = q * 3
        start = date(year, month_start, 1)
        end = _month_end(year, month_end)
        return start, end

    # Q1 2026 or 2026 Q1
    parts = period.split()
    if len(parts) == 2:
        if parts[0].startswith("Q"):
            q, year = int(parts[0][1:]), int(parts[1])
        else:
            year, q = int(parts[0]), int(parts[1][1:])
        month_start = (q - 1) * 3 + 1
        month_end = q * 3
        return date(year, month_start, 1), _month_end(year, month_end)

    # YYYY-MM
    if len(period) == 7 and period[4] == "-":
        year, month = int(period[:4]), int(period[5:])
        return date(year, month, 1), _month_end(year, month)

    # YYYY
    if len(period) == 4 and period.isdigit():
        year = int(period)
        return date(year, 1, 1), date(year, 12, 31)

    raise ValueError(f"Cannot parse period: '{period}'")


def _month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _sum_prefix(combined: dict[str, Decimal], prefix: str) -> Decimal:
    return sum(
        (v for k, v in combined.items() if k.startswith(prefix)),
        Decimal("0"),
    )


def report_pnl(entries: list[Entry], period: str | None = None) -> str:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    revenue = -_sum_prefix(combined, "income:")      # credits are negative, negate for display
    expenses = _sum_prefix(combined, "expenses:")
    net = revenue - expenses

    lines = [f"P&L{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Revenue:   {_fmt(revenue):>12}")
    lines.append(f"  Expenses:  {_fmt(expenses):>12}")
    lines.append("─" * 40)
    lines.append(f"  Net:       {_fmt(net):>12}")
    return "\n".join(lines)


def report_gst(entries: list[Entry], period: str | None = None) -> str:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    collected = -_sum_prefix(combined, "tax:hst-collected")  # stored as negative
    paid = _sum_prefix(combined, "tax:hst-paid")
    owing = collected - paid

    lines = [f"GST/HST{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Collected: {_fmt(collected):>12}")
    lines.append(f"  Paid (ITC):{_fmt(paid):>12}")
    lines.append("─" * 40)
    lines.append(f"  Net owing: {_fmt(owing):>12}")
    return "\n".join(lines)


def report_payroll(entries: list[Entry], period: str | None = None) -> str:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    salary = _sum_prefix(combined, "expenses:salary")
    tax = -_sum_prefix(combined, "liabilities:cra-tax")
    cpp = -_sum_prefix(combined, "liabilities:cra-cpp")
    ei = -_sum_prefix(combined, "liabilities:cra-ei")

    lines = [f"Payroll{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Gross salary: {_fmt(salary):>10}")
    lines.append(f"  Income tax:   {_fmt(tax):>10}")
    lines.append(f"  CPP:          {_fmt(cpp):>10}")
    lines.append(f"  EI:           {_fmt(ei):>10}")
    return "\n".join(lines)


def report_balance(entries: list[Entry], period: str | None = None) -> str:
    filtered = filter_by_period(entries, period)
    combined = aggregate(filtered)

    assets = _sum_prefix(combined, "assets:")
    liabilities = _sum_prefix(combined, "liabilities:")
    equity = _sum_prefix(combined, "equity:")
    # Net income: income/expense accounts not yet closed to equity
    net_income = _sum_prefix(combined, "income:") + _sum_prefix(combined, "expenses:")
    # Tax accounts: HST collected (liability) and paid (asset) are tracked separately
    tax = _sum_prefix(combined, "tax:")

    lines = [f"Balance Sheet{' — ' + period if period else ''}"]
    lines.append("─" * 40)
    lines.append(f"  Assets:      {_fmt(assets):>10}")
    lines.append(f"  Liabilities: {_fmt(liabilities):>10}")
    lines.append(f"  Equity:      {_fmt(equity):>10}")
    lines.append(f"  Net income:  {_fmt(net_income):>10}")
    lines.append(f"  Tax (HST):   {_fmt(tax):>10}")
    lines.append("─" * 40)
    # Global zero-sum check: all accounts across all entries must sum to zero
    check = check_balance(combined)
    lines.append(f"  Check (=0):  {_fmt(check):>10}")
    return "\n".join(lines)


def _fmt(amount: Decimal) -> str:
    return f"${amount:,.2f}"
