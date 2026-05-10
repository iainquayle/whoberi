import hashlib
import re
from decimal import Decimal
from pathlib import Path

from whoberi.types import Entry

_COLUMN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def validate_entry(entry: Entry, account_names: list[str] | None = None) -> list[str]:
    errors = []

    if not entry.balanced:
        off = sum(entry.accounts.values())
        errors.append(f"{entry.date} '{entry.meta.get('description', '')}': accounts off by {off}")

    if account_names is not None:
        for name in entry.accounts:
            if not _account_allowed(name, account_names):
                errors.append(f"{entry.date} '{entry.meta.get('description', '')}': unknown account '{name}'")

    return errors


def validate_entries(entries: list[Entry], account_names: list[str] | None = None) -> list[str]:
    errors = []
    for entry in entries:
        errors.extend(validate_entry(entry, account_names))
    errors.extend(_detect_duplicates(entries))
    return errors


def validate_column_names(headers: list[str], pattern: re.Pattern = _COLUMN_NAME_RE) -> list[str]:
    """Return list of invalid column names."""
    return [h for h in headers if not pattern.match(h)]


def _account_allowed(name: str, registry: list[str]) -> bool:
    for entry in registry:
        if entry.endswith(":") or ":" not in entry:
            # prefix match: "expenses" matches "expenses:software"
            if name == entry or name.startswith(entry.rstrip(":") + ":"):
                return True
        else:
            if name == entry:
                return True
    return False


def _row_hash(entry: Entry) -> str:
    key = f"{entry.date}|{sorted(entry.accounts.items())}|{sorted(entry.meta.items())}"
    return hashlib.sha256(key.encode()).hexdigest()


def _detect_duplicates(entries: list[Entry]) -> list[str]:
    seen: dict[str, Entry] = {}
    errors = []
    for entry in entries:
        h = _row_hash(entry)
        if h in seen:
            prior = seen[h]
            errors.append(
                f"Duplicate entry: {entry.date} '{entry.meta.get('description', '')}' "
                f"(matches entry on {prior.date})"
            )
        else:
            seen[h] = entry
    return errors
