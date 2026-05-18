import pytest

from whoberi.reporting.reporter_discovery import build_reporter_registry, load_reporters
from whoberi.reporting.reports import BUILTIN_REPORTERS, make_context
from tests.conftest import FIXTURES, FULL_REGISTRY, SAMPLE_ENTRIES


def test_no_reports_dir_returns_empty(tmp_path):
    assert load_reporters(tmp_path / "nonexistent") == {}


def test_reporters_loaded_from_fixtures():
    reporters = load_reporters(FIXTURES / "reports")
    assert "gst" in reporters
    assert "payroll" in reporters


def test_missing_attribute_raises(tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "bad.py").write_text('NAME = "bad"\n')
    with pytest.raises(ValueError, match="missing required attribute"):
        load_reporters(reports_dir)


def test_reporter_with_syntax_error_raises_clear_error(tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "bad.py").write_text("this is not python!!!\n")
    with pytest.raises(ValueError, match="Failed to load reporter 'bad.py'"):
        load_reporters(reports_dir)


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


@pytest.mark.parametrize("reserved", ["list", "all"])
def test_reporter_with_reserved_name_raises(tmp_path, reserved):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "bad.py").write_text(
        f'NAME = "{reserved}"\nDESCRIPTION = "x"\ndef report(ctx): return ""\n'
    )
    with pytest.raises(ValueError, match="reserved"):
        load_reporters(reports_dir)


@pytest.mark.parametrize("source,match", [
    ('NAME = 42\nDESCRIPTION = "x"\ndef report(ctx): return ""\n', "NAME must be a string"),
    ('NAME = "x"\nDESCRIPTION = 42\ndef report(ctx): return ""\n', "DESCRIPTION must be a string"),
    ('NAME = "x"\nDESCRIPTION = "x"\nreport = 42\n', "report must be callable"),
])
def test_reporter_attribute_type_checks(tmp_path, source, match):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "bad.py").write_text(source)
    with pytest.raises(ValueError, match=match):
        load_reporters(reports_dir)
