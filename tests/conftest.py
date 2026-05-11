from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from whoberi.types import Entry

FIXTURES = Path(__file__).parent / "fixtures"


def make_entry(accounts: dict[str, Decimal], d: date = date(2026, 1, 1), desc: str = "test") -> Entry:
    return Entry(date=d, accounts=accounts, meta={"description": desc})
