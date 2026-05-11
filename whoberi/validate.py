import re

from whoberi.accounts import AccountRegistry
from whoberi.hashing import row_hash
from whoberi.types import Entry

_COLUMN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def validate_entry(entry: Entry, registry: AccountRegistry | None = None) -> list[str]:
    errors = []

    off = sum(entry.accounts.values())
    if off != 0:
        errors.append(f"{entry.date} '{entry.meta.get('description', '')}': accounts off by {off}")

    if registry is not None:
        for name in entry.accounts:
            if not registry.is_known(name):
                errors.append(f"{entry.date} '{entry.meta.get('description', '')}': unknown account '{name}'")

    return errors


def validate_entries(entries: list[Entry], registry: AccountRegistry | None = None) -> list[str]:
    errors = []
    for entry in entries:
        errors.extend(validate_entry(entry, registry))
    errors.extend(_detect_duplicates(entries))
    return errors


def validate_column_names(headers: list[str]) -> list[str]:
    return [h for h in headers if not _COLUMN_NAME_RE.match(h)]


def _detect_duplicates(entries: list[Entry]) -> list[str]:
    seen: dict[str, Entry] = {}
    errors = []
    for entry in entries:
        h = row_hash({"date": str(entry.date), **entry.accounts, **entry.meta})
        if h in seen:
            prior = seen[h]
            errors.append(
                f"Duplicate entry: {entry.date} '{entry.meta.get('description', '')}' "
                f"(matches entry on {prior.date})"
            )
        else:
            seen[h] = entry
    return errors
