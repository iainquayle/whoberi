"""Tests for the Books cross-ledger source-row accessor."""
from decimal import Decimal
from pathlib import Path

import pytest

from whoberi.aggregate import check_balance
from whoberi.ledgers.books import Books
from whoberi.main import run_pipeline


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_rows_reads_another_books_source_rows(tmp_path):
    src = tmp_path / "income" / "fooco.csv"
    _write(src, "date,amount\n2026-01-01,100\n2026-02-01,200\n")
    books = Books({"income/fooco": src})
    rows = list(books.rows("income/fooco"))
    assert [r["amount"] for r in rows] == ["100", "200"]


def test_rows_unknown_name_raises_listing_available(tmp_path):
    books = Books({"income/fooco": tmp_path / "f.csv", "expenses/sw": tmp_path / "s.csv"})
    with pytest.raises(KeyError) as exc:
        books.rows("nope")
    msg = str(exc.value)
    assert "nope" in msg
    assert "income/fooco" in msg and "expenses/sw" in msg


def test_rows_yields_fresh_iterator_each_call(tmp_path):
    src = tmp_path / "b.csv"
    _write(src, "date,amount\n2026-01-01,100\n")
    books = Books({"b": src})
    assert list(books.rows("b")) == list(books.rows("b"))  # re-iterable; not exhausted


def test_names_sorted(tmp_path):
    books = Books({"b": tmp_path / "b.csv", "a": tmp_path / "a.csv"})
    assert books.names() == ("a", "b")


def test_handler_reads_sibling_book_through_pipeline(tmp_path):
    """End-to-end: a handler sums a sibling book's source rows via run_pipeline.

    `tally` is processed before `sales` (sorted order) yet reads its rows fine —
    source rows are order-independent.
    """
    (tmp_path / "config.toml").write_text(
        '[dirs]\nledgers = "books"\nimports = "imports"\nreports = "reports"\n'
        '[accounts]\nasset = ["cash", "tally"]\nincome = ["sales"]\nequity = ["tally-offset"]\n'
    )
    books_dir = tmp_path / "books"
    _write(books_dir / "sales.csv", "date,amount\n2026-01-01,100\n2026-02-01,200\n")
    _write(
        books_dir / "sales.py",
        "from datetime import date\nfrom decimal import Decimal\n"
        "from whoberi.types import Entry\n"
        "def process(rows, config, meta, books):\n"
        "    for r in rows:\n"
        "        amt = Decimal(r['amount'])\n"
        "        yield Entry(date=date.fromisoformat(r['date']),\n"
        "                    accounts={'cash': amt, 'sales': amt})\n",
    )
    _write(books_dir / "tally.csv", "date,amount\n")  # header only; ignores own rows
    _write(
        books_dir / "tally.py",
        "from datetime import date\nfrom decimal import Decimal\n"
        "from whoberi.types import Entry\n"
        "def process(rows, config, meta, books):\n"
        "    total = sum(Decimal(r['amount']) for r in books.rows('sales'))\n"
        "    return [Entry(date=date(2026, 1, 1),\n"
        "                  accounts={'tally': total, 'tally-offset': total})]\n",
    )
    result = run_pipeline(tmp_path)
    tally = next(e for e in result.entries if "tally" in e.accounts)
    assert tally.accounts["tally"] == Decimal("300")
    assert check_balance(result.combined, result.registry) == 0
