import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from whoberi.accounts import AccountRegistry, AccountType
from whoberi.types import Entry

FIXTURES = Path(__file__).parent / "fixtures"


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
    expense=["meals", "software", "salary", "recurring", "flights"],
)
