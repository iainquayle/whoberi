"""Bank CSV import — match rows to target ledgers via pattern rules. Pure match + IO persist."""
import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

from whoberi.hashing import row_hash
from whoberi.ledgers.csv_io import read_csv


def match_rows(
    rows: Iterable[dict],
    rules: dict[str, str],
) -> Iterator[tuple[dict, str | None]]:
    """
    For each row, yield (row, target_ledger | None).
    target_ledger is the first rule whose pattern (case-insensitive substring) matches
    the row's 'description' field, or None if no rule matched.
    """
    for row in rows:
        description = row.get("description", "")
        yield row, _match_rule(description, rules)


def persist_matches(
    matches: Iterable[tuple[dict, str]],
    ledgers_root: Path,
) -> tuple[int, int]:
    """
    Append matched rows to their target ledger CSVs.
    Duplicate rows (already present by full-row hash) are skipped.
    Returns (written, skipped).
    """
    existing_hashes: dict[Path, set[str]] = {}
    written = 0
    skipped = 0
    for row, target_ledger in matches:
        target_path = ledgers_root / (target_ledger + ".csv")
        if target_path not in existing_hashes:
            existing_hashes[target_path] = {
                row_hash(r) for r in (read_csv(target_path) if target_path.exists() else [])
            }
        h = row_hash(row)
        if h in existing_hashes[target_path]:
            skipped += 1
            continue
        _append_row(row, target_path)
        existing_hashes[target_path].add(h)
        written += 1
    return written, skipped


def _match_rule(description: str, rules: dict[str, str]) -> str | None:
    desc_upper = description.upper()
    for pattern, target in rules.items():
        if pattern.upper() in desc_upper:
            return target
    return None


def _append_row(row: dict, target_path: Path) -> None:
    if target_path.exists() and target_path.stat().st_size > 0:
        with open(target_path, newline="") as f:
            existing_header = next(csv.reader(f), None)
        if existing_header is None:
            fieldnames = list(row.keys())
            write_header = True
        else:
            if set(existing_header) != set(row.keys()):
                raise ValueError(
                    f"{target_path}: column mismatch — existing {existing_header}, "
                    f"incoming {list(row.keys())}"
                )
            fieldnames = existing_header
            write_header = False
    else:
        fieldnames = list(row.keys())
        write_header = True
    with open(target_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
