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
    (["accounts"], "venn-cad"),
    (["status"], "Asset"),
    (["report", "pnl"], "Revenue"),
    (["report", "gst"], "Collected"),
    (["report", "balance"], "$0.00"),
    (["report", "accounts"], "asset"),
    (["report", "list"], "pnl"),
])
def test_subcommand(args, expected):
    result = run(*args)
    assert result.returncode == 0
    assert expected in result.stdout


def test_report_pnl_with_period():
    result = run("report", "pnl", "--period", "Q1 2026")
    assert result.returncode == 0
    assert "Q1 2026" in result.stdout


def test_report_unknown_exits_nonzero():
    result = run("report", "nonexistent")
    assert result.returncode != 0
    assert "available" in result.stderr


def test_missing_root_reports_error():
    result = run("validate", root=Path("/nonexistent/path"))
    assert result.returncode != 0
