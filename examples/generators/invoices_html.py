"""One HTML invoice per income entry.

Inputs are found by ledger prefix ('income/'), not hardcoded: adding a client means
adding a ledger file. The ledger stem is both the income account and the key into
[consts.clients], so a client missing from config.toml raises a KeyError naming it.
"""
from datetime import date
from decimal import Decimal

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.documents.types import Document
from whoberi.types import Entry

NAME = "invoices"
DESCRIPTION = "One HTML invoice per income entry"


def generate(ctx):
    company = ctx.config["consts"]["company"]
    clients = ctx.config["consts"]["clients"]
    for key, entries in ctx.by_ledger().items():
        directory, _, stem = key.rpartition("/")
        if directory != "income":
            continue
        client = clients[stem]
        for entry in entries:
            yield Document(
                name=f"invoices/{entry.date}-{stem}.html",
                payload=_render(company, client, entry, _lines(ctx.registry, entry, stem), ctx.fmt),
            )


def _lines(registry: AccountRegistry, entry: Entry, stem: str) -> list[tuple[str, Decimal]]:
    """Split one entry into invoice lines: revenue, tax, and the cash total."""
    total = sum(
        (v for a, v in entry.accounts.items() if registry.type_of(a) == AccountType.ASSET),
        Decimal("0"),
    )
    subtotal = entry.accounts[stem]
    return [("Subtotal", subtotal), ("Tax", total - subtotal), ("Total", total)]


def _render(company: dict, client: dict, entry: Entry, lines: list, fmt) -> str:
    rows = "\n".join(f"  <tr><td>{label}</td><td>{fmt(amount)}</td></tr>" for label, amount in lines)
    return f"""<!doctype html>
<title>Invoice — {client['name']} — {entry.date}</title>
<h1>{company['name']}</h1>
<p>{company['address']}<br>GST/HST {company['gst']}</p>
<h2>Bill to: {client['name']}</h2>
<p>{client['address']}<br>Terms: {client['terms']}</p>
<p>Date: {entry.date}<br>{entry.meta['description']}</p>
<table>
{rows}
</table>
"""


def _test_lines_split_revenue_from_tax():
    registry = AccountRegistry({
        AccountType.ASSET: {"cash"},
        AccountType.INCOME: {"fooco"},
        AccountType.LIABILITY: {"hst-collected"},
    })
    entry = Entry(
        date=date(2026, 1, 1),
        accounts={"cash": Decimal("113"), "fooco": Decimal("100"), "hst-collected": Decimal("13")},
    )
    assert _lines(registry, entry, "fooco") == [
        ("Subtotal", Decimal("100")),
        ("Tax", Decimal("13")),
        ("Total", Decimal("113")),
    ]
