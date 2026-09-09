"""Reporter-specific discovery; the generic plugin rules live in test_plugins.py."""
import pytest

from whoberi.reporting.reporter_discovery import build_reporter_registry, load_reporters
from whoberi.reporting.reports import BUILTIN_REPORTERS, make_context
from tests.conftest import FIXTURES, FULL_REGISTRY, SAMPLE_ENTRIES


def test_reporters_loaded_from_fixtures():
    reporters = load_reporters(FIXTURES / "reports")
    assert "gst" in reporters
    assert "payroll" in reporters


def test_builtin_shadow_raises():
    custom = {"pnl": BUILTIN_REPORTERS["pnl"]}
    with pytest.raises(ValueError, match="conflict with built-in"):
        build_reporter_registry(BUILTIN_REPORTERS, custom)


@pytest.mark.parametrize("report_name,expected_substrings", [
    ("gst", ["$603.98", "$18.12"]),
    ("payroll", ["$5,000.00", "$1,000.00", "$300.00"]),
])
def test_fixture_reporter_values(report_name, expected_substrings):
    reporters = load_reporters(FIXTURES / "reports")
    ctx = make_context(SAMPLE_ENTRIES, FULL_REGISTRY, "Q1 2026")
    out = reporters[report_name].fn(ctx)
    for s in expected_substrings:
        assert s in out
