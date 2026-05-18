import re
from collections.abc import Iterable

from whoberi.accounts import AccountRegistry
from whoberi.hashing import row_hash
from whoberi.types import Entry

_COLUMN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def validate_entry(entry: Entry, registry: AccountRegistry) -> list[str]:
    errors = []

    if not entry.balanced:
        off = sum(entry.accounts.values())
        errors.append(f"{entry.date} '{entry.meta.get('description', '')}': accounts off by {off}")

    for name in entry.accounts:
        if not registry.is_known(name):
            errors.append(f"{entry.date} '{entry.meta.get('description', '')}': unknown account '{name}'")

    return errors


def validate_entries(entries: Iterable[Entry], registry: AccountRegistry) -> list[str]:
    errors: list[str] = []
    seen: dict[str, Entry] = {}
    for entry in entries:
        errors.extend(validate_entry(entry, registry))
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


def validate_column_names(headers: Iterable[str]) -> list[str]:
    return [h for h in headers if not _COLUMN_NAME_RE.match(h)]
