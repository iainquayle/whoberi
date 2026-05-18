import re
from collections.abc import Iterable

from whoberi.accounts import AccountRegistry
from whoberi.aggregate import check_balance
from whoberi.hashing import row_hash
from whoberi.types import Entry

_COLUMN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def validate_entry(entry: Entry, registry: AccountRegistry) -> list[str]:
    errors = []
    unknown = [name for name in entry.accounts if not registry.is_known(name)]
    for name in unknown:
        errors.append(f"{entry.date} '{entry.meta.get('description', '')}': unknown account '{name}'")
    if not unknown:
        off = check_balance(entry.accounts, registry)
        if off != 0:
            errors.append(f"{entry.date} '{entry.meta.get('description', '')}': accounts off by {off}")
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
