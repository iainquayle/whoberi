from dataclasses import dataclass
from decimal import Decimal

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.aggregate import aggregate
from whoberi.money import fmt_money
from whoberi.period import filter_as_of, filter_by_period, period_end_str
from whoberi.reporting.reporter_context import ReporterContext
from whoberi.reporting.reporter_discovery import ReporterDef
from whoberi.types import Entry


@dataclass(frozen=True)
class Section:
    header: str
    rows: list[tuple[str, Decimal]]
    total_label: str
    total: Decimal


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


def _render_statement(title: str, sections: list[Section], final: tuple[str, Decimal]) -> str:
    candidates: list[str] = []
    for section in sections:
        candidates.extend(n for n, _ in section.rows)
        candidates.append(section.total_label)
    candidates.append(final[0])
    label_width = max((len(c) for c in candidates), default=10)
    divider_width = label_width + 20  # 4 indent + label + 2 gap + 14 amount

    lines = [title, "─" * divider_width]
    for i, section in enumerate(sections):
        if i > 0:
            lines.append("")
        lines.append(f"  {section.header}")
        for name, amount in section.rows:
            lines.append(f"    {name:<{label_width}}  {fmt_money(amount):>14}")
        lines.append(f"    {section.total_label:<{label_width}}  {fmt_money(section.total):>14}")
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

    end = period_end_str(ctx.period)
    title = f"Income Statement — for the period ended {end}" if end else "Income Statement — for all entries"

    sections = [
        Section("REVENUE", sorted(revenue_accounts.items()), "Total revenue", revenue_total),
        Section("EXPENSES", sorted(expense_accounts.items()), "Total expenses", expenses_total),
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

    end = period_end_str(ctx.period)
    title = f"Balance Sheet — as at {end}" if end else "Balance Sheet"

    sections = [
        Section("ASSETS", sorted(assets.items()), "Total assets", total_assets),
        Section("LIABILITIES", sorted(liabilities.items()), "Total liabilities", total_liabilities),
        Section("EQUITY", equity_rows, "Total equity", total_equity),
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
