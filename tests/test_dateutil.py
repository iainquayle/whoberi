from datetime import date

import pytest

from whoberi.dateutil import expand_dates


@pytest.mark.parametrize("start,as_of,end,expected", [
    # Monthly across multiple months
    (date(2026, 1, 1), date(2026, 5, 10), None,
     [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)]),
    # Monthly with end_date caps early
    (date(2026, 1, 1), date(2026, 12, 31), date(2026, 3, 15),
     [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]),
    # as_of caps before end_date
    (date(2026, 1, 1), date(2026, 2, 15), date(2026, 6, 1),
     [date(2026, 1, 1), date(2026, 2, 1)]),
    # Start after as_of yields nothing
    (date(2026, 6, 1), date(2026, 1, 1), None, []),
    # Day 31 clamps in short months
    (date(2026, 1, 31), date(2026, 4, 30), None,
     [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]),
])
def test_monthly(start, as_of, end, expected):
    assert list(expand_dates(start, "monthly", as_of, end)) == expected


def test_semi_monthly():
    result = list(expand_dates(date(2026, 1, 1), "semi-monthly", date(2026, 2, 28)))
    assert result == [date(2026, 1, 1), date(2026, 1, 15), date(2026, 2, 1), date(2026, 2, 15)]


def test_semi_monthly_start_mid_month():
    # start on the 15th — the 1st of that month should be skipped
    result = list(expand_dates(date(2026, 1, 15), "semi-monthly", date(2026, 2, 15)))
    assert result == [date(2026, 1, 15), date(2026, 2, 1), date(2026, 2, 15)]


def test_weekly():
    result = list(expand_dates(date(2026, 1, 1), "weekly", date(2026, 1, 22)))
    assert result == [date(2026, 1, 1), date(2026, 1, 8), date(2026, 1, 15), date(2026, 1, 22)]


def test_unknown_period_raises():
    with pytest.raises(ValueError, match="Unknown period"):
        list(expand_dates(date(2026, 1, 1), "fortnightly", date(2026, 12, 31)))
