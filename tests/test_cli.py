"""End-to-end CLI tests using the fixture data directory."""
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import FIXTURES

PYTHON = sys.executable


def run(*args: str, root: Path = FIXTURES) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, "-m", "whoberi.main", "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("args,expected", [
    (["discover"], "software"),
    (["validate"], "OK"),
    (["heal"], "No changes"),
    (["accounts"], "venn-cad"),
    (["status"], "Asset"),
    (["report", "pnl"], "REVENUE"),
    (["report", "gst"], "Collected"),
    (["report", "balance"], "Total assets"),
    (["report", "balance", "--period", "Q1 2026"], "as at 2026-03-31"),
    (["report", "accounts"], "asset"),
    (["report", "list"], "pnl"),
    (["report", "all"], "Income Statement"),
])
def test_subcommand(args, expected):
    result = run(*args)
    assert result.returncode == 0
    assert expected in result.stdout


def test_report_pnl_with_period():
    result = run("report", "pnl", "--period", "Q1 2026")
    assert result.returncode == 0
    assert "for the period ended 2026-03-31" in result.stdout


def test_report_unknown_exits_nonzero():
    result = run("report", "nonexistent")
    assert result.returncode != 0
    assert "available" in result.stderr


def test_missing_root_reports_error():
    result = run("validate", root=Path("/nonexistent/path"))
    assert result.returncode != 0


def test_missing_config_clean_error(tmp_path):
    result = run("validate", root=tmp_path)
    assert result.returncode != 0
    assert "ERROR: config.toml not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_report_does_not_mutate_csvs(tmp_path):
    """Read-only commands must not rewrite ledger files."""
    import shutil
    shutil.copytree(FIXTURES, tmp_path / "root")
    root = tmp_path / "root"
    csvs = list((root / "books").rglob("*.csv"))
    mtimes = {p: p.stat().st_mtime for p in csvs}
    result = run("report", "pnl", root=root)
    assert result.returncode == 0
    for p, mtime in mtimes.items():
        assert p.stat().st_mtime == mtime, f"report mutated {p}"


def test_heal_rewrites_dirty_csv(tmp_path):
    """heal should sort out-of-order rows."""
    import shutil
    shutil.copytree(FIXTURES, tmp_path / "root")
    root = tmp_path / "root"
    target = root / "books" / "expenses" / "software.csv"
    original = target.read_text()
    # Reverse all rows after the header to dirty the file
    header, *rows = original.strip().split("\n")
    target.write_text("\n".join([header, *reversed(rows)]) + "\n")
    result = run("heal", root=root)
    assert result.returncode == 0
    assert "sorted" in result.stdout
    assert target.read_text() == original


def _fixture_copy(tmp_path):
    import shutil
    shutil.copytree(FIXTURES, tmp_path / "root")
    return tmp_path / "root"


def test_add_appends_row(tmp_path):
    root = _fixture_copy(tmp_path)
    target = root / "books" / "expenses" / "software.csv"
    before = target.read_text().count("\n")
    result = run("add", "expenses/software", "2026-03-01", "GHI", "200.00", root=root)
    assert result.returncode == 0, result.stderr
    assert target.read_text().count("\n") == before + 1
    assert "2026-03-01,GHI,200.00" in target.read_text()


def test_add_unknown_ledger(tmp_path):
    root = _fixture_copy(tmp_path)
    result = run("add", "expenses/ghost", "2026-03-01", "X", "1.00", root=root)
    assert result.returncode != 0
    assert "Ledger not found" in result.stderr


def test_add_field_count_mismatch(tmp_path):
    root = _fixture_copy(tmp_path)
    result = run("add", "expenses/software", "2026-03-01", "only-two", root=root)
    assert result.returncode != 0
    assert "Expected 3 fields" in result.stderr


def test_report_rejects_unbalanced_entry(tmp_path):
    """report must validate first; unbalanced entries are a fatal error, not silent corruption."""
    root = _fixture_copy(tmp_path)
    bad = root / "books" / "expenses" / "software.csv"
    bad.write_text(bad.read_text() + "2026-03-01,BUG,abc\n")  # invalid Decimal — pipeline fails
    result = run("report", "pnl", root=root)
    assert result.returncode != 0


def test_report_list_works_with_broken_handler(tmp_path):
    """`report list` should only need config + reporters, not a working pipeline."""
    root = _fixture_copy(tmp_path)
    (root / "books" / "expenses" / "software.py").write_text("this is not python!!!\n")
    result = run("report", "list", root=root)
    assert result.returncode == 0
    assert "pnl" in result.stdout


def test_report_pnl_with_genuinely_unbalanced(tmp_path):
    """Construct an unbalanced entry via a bad handler; report must exit non-zero."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "config.toml").write_text(
        '[dirs]\nledgers = "books"\nimports = "imports"\nreports = "reports"\n'
        '[accounts]\nasset = ["cash"]\nincome = ["sales"]\n'
    )
    books = root / "books"
    books.mkdir()
    (books / "sales.csv").write_text("date,amount\n2026-01-01,100\n")
    (books / "sales.py").write_text(
        "from datetime import date\nfrom decimal import Decimal\n"
        "from whoberi.types import Entry\n"
        "def process(rows, config, meta):\n"
        "    for r in rows:\n"
        "        yield Entry(date=date.fromisoformat(r['date']),\n"
        "                    accounts={'cash': Decimal('100'), 'sales': Decimal('-50')})\n"
    )
    result = run("report", "pnl", root=root)
    assert result.returncode != 0
    assert "off by" in result.stderr
