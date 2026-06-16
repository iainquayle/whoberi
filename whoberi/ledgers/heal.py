"""Heal: sort chronologically, remove duplicate rows. Pure logic + file orchestrator."""
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from whoberi.hashing import row_hash
from whoberi.ledgers.delimited_io import read_rows_with_headers, write_rows


def heal(rows: Iterable[dict]) -> tuple[list[dict], list[str]]:
    """
    Sort rows by date and remove duplicate rows (by full-row hash).
    Returns (healed rows, log messages). Empty log means no change.
    Dates must be ISO 8601 (YYYY-MM-DD); other formats raise ValueError.
    """
    materialized = list(rows)
    if not materialized:
        return [], []

    logs: list[str] = []
    seen: set[str] = set()
    deduped: list[dict] = []
    for row in materialized:
        h = row_hash(row)
        if h in seen:
            logs.append(f"removed duplicate row: {dict(row)}")
        else:
            seen.add(h)
            deduped.append(row)

    sorted_rows = sorted(deduped, key=_parse_date)
    if sorted_rows != deduped:
        logs.append(f"re-sorted chronologically ({len(sorted_rows)} rows)")

    return sorted_rows, logs


def _parse_date(row: dict) -> date:
    raw = row["date"]
    try:
        return date.fromisoformat(raw)
    except ValueError as e:
        raise ValueError(f"row date is not ISO 8601 ({raw!r}): {dict(row)}") from e


def heal_file(path: Path) -> list[str]:
    """Read, heal, and rewrite a ledger in place if anything changed. Returns log messages."""
    if not path.exists():
        return []
    headers, rows = read_rows_with_headers(path)
    if not headers or not rows:
        return []
    healed, logs = heal(rows)
    if not logs:
        return []
    write_rows(path, headers, healed)
    return [f"heal {path.name}: {msg}" for msg in logs]
