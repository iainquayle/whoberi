import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.types import Entry

FIXTURES = Path(__file__).parent.parent / "examples"

CSV_FIELDS = ["date", "description", "amount"]


def make_entry(accounts: dict[str, Decimal], d: date = date(2026, 1, 1), desc: str = "test") -> Entry:
    return Entry(date=d, accounts=accounts, meta={"description": desc})


def make_registry(**kwargs) -> AccountRegistry:
    return AccountRegistry({AccountType(k): set(v) for k, v in kwargs.items()})


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


FULL_REGISTRY = make_registry(
    asset=["venn-cad", "hst-paid"],
    liability=["cra-tax", "cra-cpp", "cra-ei", "hst-collected"],
    equity=["draws", "retained-earnings"],
    income=["fooco", "barco"],
    expense=["meals", "software", "salary", "recurring"],
)

SAMPLE_ENTRIES = [
    # Q1: income 5250 HST-inclusive
    make_entry({"venn-cad": Decimal("5250"), "fooco": Decimal("-4646.02"), "hst-collected": Decimal("-603.98")}, d=date(2026, 1, 15)),
    # Q1: expense 157.50 HST-inclusive
    make_entry({"software": Decimal("139.38"), "hst-paid": Decimal("18.12"), "venn-cad": Decimal("-157.50")}, d=date(2026, 2, 1)),
    # Q2: income
    make_entry({"venn-cad": Decimal("2260"), "fooco": Decimal("-2000"), "hst-collected": Decimal("-260")}, d=date(2026, 4, 10)),
    # Payroll Q1
    make_entry({"salary": Decimal("5000"), "cra-tax": Decimal("-1000"), "cra-cpp": Decimal("-300"), "cra-ei": Decimal("-150"), "venn-cad": Decimal("-3550")}, d=date(2026, 1, 15)),
    # Draw Q1
    make_entry({"draws": Decimal("3000"), "venn-cad": Decimal("-3000")}, d=date(2026, 1, 20)),
]
