"""Trial balance as a single CSV — the file an accountant asks for."""
import csv
import io

from whoberi.documents.types import Document

NAME = "trial-balance"
DESCRIPTION = "Trial balance as one CSV — account, type, balance"


def generate(ctx):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["account", "type", "balance"])
    for account in sorted(ctx.combined):
        writer.writerow([
            account,
            ctx.registry.type_of(account).value,
            f"{ctx.combined[account]:.2f}",
        ])
    yield Document(name=_filename(ctx.period), payload=buf.getvalue())


def _filename(period: str | None) -> str:
    stem = "trial-balance" if period is None else f"trial-balance-{period}"
    return f"{stem.replace(' ', '-')}.csv"


def _test_filename():
    assert _filename(None) == "trial-balance.csv"
    assert _filename("Q1 2026") == "trial-balance-Q1-2026.csv"
