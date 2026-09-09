import pytest

from whoberi.period import filter_as_of, filter_by_period, parse_period, period_end_str
from tests.conftest import SAMPLE_ENTRIES


@pytest.mark.parametrize("period,expected_count", [
    ("Q1 2026", 4),
    ("Q2 2026", 1),
    ("2026-01", 3),
    ("2026", 5),
])
def test_filter_by_period(period, expected_count):
    assert len(list(filter_by_period(SAMPLE_ENTRIES, period))) == expected_count


def test_filter_none_returns_all():
    assert list(filter_by_period(SAMPLE_ENTRIES, None)) == SAMPLE_ENTRIES


def test_filter_as_of():
    assert len(list(filter_as_of(SAMPLE_ENTRIES, "Q1 2026"))) == 4


def test_invalid_period_raises():
    with pytest.raises(ValueError, match="Cannot parse period"):
        list(filter_by_period(SAMPLE_ENTRIES, "not-a-period"))


@pytest.mark.parametrize("period,expected", [
    ("Q1 2026", "2026-03-31"),
    ("2026-02", "2026-02-28"),
    ("2026", "2026-12-31"),
    (None, None),
])
def test_period_end_str(period, expected):
    assert period_end_str(period) == expected


def test_parse_period_is_case_insensitive():
    assert parse_period("q1 2026") == parse_period("Q1 2026")
