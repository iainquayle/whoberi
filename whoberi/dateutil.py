"""Date sequence expansion for recurring transactions."""
import calendar
from collections.abc import Iterator
from datetime import date, timedelta


def expand_dates(
    start: date,
    period: str,
    as_of: date,
    end: date | None = None,
) -> Iterator[date]:
    """Yield dates from start through min(end, as_of) at the given period."""
    cutoff = min(end, as_of) if end else as_of
    if period not in _BUILDERS:
        raise ValueError(f"Unknown period: {period!r}")
    return _BUILDERS[period](start, cutoff)


def _next_month(year: int, month: int) -> tuple[int, int]:
    month += 1
    if month > 12:
        return year + 1, 1
    return year, month


def _monthly(start: date, cutoff: date) -> Iterator[date]:
    year, month, day = start.year, start.month, start.day
    while True:
        last = calendar.monthrange(year, month)[1]
        d = date(year, month, min(day, last))
        if d > cutoff:
            break
        yield d
        year, month = _next_month(year, month)


def _semi_monthly(start: date, cutoff: date) -> Iterator[date]:
    year, month = start.year, start.month
    while True:
        for day in (1, 15):
            d = date(year, month, day)
            if d < start:
                continue
            if d > cutoff:
                return
            yield d
        year, month = _next_month(year, month)


def _weekly(start: date, cutoff: date) -> Iterator[date]:
    current = start
    while current <= cutoff:
        yield current
        current += timedelta(weeks=1)


_BUILDERS = {"monthly": _monthly, "semi-monthly": _semi_monthly, "weekly": _weekly}
