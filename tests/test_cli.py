"""End-to-end CLI tests using the fixture data directory."""
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
PYTHON = sys.executable


def run(*args: str, root: Path = FIXTURES) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, "-m", "whoberi.main", "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


def test_discover_exits_zero():
    result = run("discover")
    assert result.returncode == 0
    assert "software" in result.stdout


def test_validate_exits_zero_for_valid_data():
    result = run("validate")
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_accounts_shows_balances():
    result = run("accounts")
    assert result.returncode == 0
    assert "assets:venn-cad" in result.stdout
    assert "Balance check" in result.stdout


def test_status_exits_zero():
    result = run("status")
    assert result.returncode == 0
    assert "Cash" in result.stdout


def test_report_pnl():
    result = run("report", "pnl")
    assert result.returncode == 0
    assert "Revenue" in result.stdout
    assert "Expenses" in result.stdout


def test_report_gst():
    result = run("report", "gst")
    assert result.returncode == 0
    assert "Collected" in result.stdout


def test_report_pnl_with_period():
    result = run("report", "pnl", "--period", "Q1 2026")
    assert result.returncode == 0
    assert "Q1 2026" in result.stdout


def test_report_balance():
    result = run("report", "balance")
    assert result.returncode == 0
    assert "Check (=0)" in result.stdout
    assert "$0.00" in result.stdout


def test_missing_root_reports_error():
    result = run("validate", root=Path("/nonexistent/path"))
    assert result.returncode != 0
