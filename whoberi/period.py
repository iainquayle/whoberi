"""Period parsing and entry filters. Shared by reporting and documents."""
import calendar
import re
from collections.abc import Iterable, Iterator
from datetime import date

from whoberi.types import Entry


def filter_by_period(entries: Iterable[Entry], period: str | None) -> Iterator[Entry]:
    if period is None:
        return iter(entries)
    start, end = parse_period(period)
    return (e for e in entries if start <= e.date <= end)


def filter_as_of(entries: Iterable[Entry], period: str | None) -> Iterator[Entry]:
    if period is None:
        return iter(entries)
    _, end = parse_period(period)
    return (e for e in entries if e.date <= end)


def period_end_str(period: str | None) -> str | None:
    if period is None:
        return None
    return parse_period(period)[1].isoformat()


def _quarter(m: re.Match) -> tuple[date, date]:
    q, year = int(m.group(1)), int(m.group(2))
    month_start = (q - 1) * 3 + 1
    return date(year, month_start, 1), _month_end(year, month_start + 2)


def _month_from_match(m: re.Match) -> tuple[date, date]:
    year, month = int(m.group(1)), int(m.group(2))
    return date(year, month, 1), _month_end(year, month)


def _year_from_match(m: re.Match) -> tuple[date, date]:
    year = int(m.group(1))
    return date(year, 1, 1), date(year, 12, 31)


_PERIOD_PATTERNS = [
    (re.compile(r"^Q([1-4]) (\d{4})$"), _quarter),
    (re.compile(r"^(\d{4})-(\d{2})$"), _month_from_match),
    (re.compile(r"^(\d{4})$"), _year_from_match),
]


def parse_period(period: str) -> tuple[date, date]:
    s = period.strip().upper()
    for pattern, builder in _PERIOD_PATTERNS:
        m = pattern.match(s)
        if m:
            return builder(m)
    raise ValueError(
        f"Cannot parse period: '{period}' — valid formats: 'Q1 2026', '2026-01', '2026'"
    )


def _month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)
