from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass
class LedgerMeta:
    name: str          # CSV stem: "software", "fooco"
    directory: str     # parent dir name: "expenses", "income"
    path: Path         # full path to the CSV
    overrides: dict = field(default_factory=dict)  # per-ledger .toml contents


@dataclass
class Entry:
    date: date
    accounts: dict[str, Decimal]
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def balanced(self) -> bool:
        return sum(self.accounts.values()) == Decimal("0")
