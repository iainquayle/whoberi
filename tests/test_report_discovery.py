import pytest

from whoberi.report_discovery import build_registry, load_plugins
from whoberi.reports import BUILTIN_REPORTS, make_context
from tests.conftest import FIXTURES, FULL_REGISTRY, SAMPLE_ENTRIES


def test_no_reports_dir_returns_empty(tmp_path):
    assert load_plugins(tmp_path / "nonexistent") == {}


def test_plugins_loaded_from_fixtures():
    plugins = load_plugins(FIXTURES / "reports")
    assert "gst" in plugins
    assert "payroll" in plugins


def test_missing_attribute_raises(tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "bad.py").write_text('NAME = "bad"\n')
    with pytest.raises(ValueError, match="missing required attribute"):
        load_plugins(reports_dir)


def test_builtin_shadow_raises():
    custom = {"pnl": BUILTIN_REPORTS["pnl"]}
    with pytest.raises(ValueError, match="conflict with built-in"):
        build_registry(BUILTIN_REPORTS, custom)


@pytest.mark.parametrize("report_name,expected_substrings", [
    ("gst", ["$603.98", "$18.12"]),
    ("payroll", ["$5,000.00", "$1,000.00", "$300.00"]),
])
def test_fixture_report_values(report_name, expected_substrings):
    plugins = load_plugins(FIXTURES / "reports")
    ctx = make_context(SAMPLE_ENTRIES, FULL_REGISTRY, "Q1 2026")
    out = plugins[report_name].fn(ctx)
    for s in expected_substrings:
        assert s in out
