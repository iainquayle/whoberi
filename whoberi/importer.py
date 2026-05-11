"""Bank CSV import — match rows to target ledger CSVs via pattern rules."""
import csv
from pathlib import Path

from whoberi.discover import read_csv
from whoberi.hashing import row_hash


def import_bank_csv(
    source: Path,
    rules: dict[str, str],
    root: Path,
) -> tuple[list[dict], list[dict]]:
    """
    Match rows from source CSV against rules.

    rules: {pattern: target_ledger} where pattern is a substring to match against
           the description field, and target_ledger is a relative path (no .csv).

    Returns (matched, unmatched). Matched rows are appended to their target CSVs.
    Duplicate rows (already present) are skipped silently.
    """
    rows = read_csv(source)
    matched = []
    unmatched = []

    # Build per-target hash sets once to avoid re-reading CSVs per row
    existing_hashes: dict[Path, set[str]] = {}

    for row in rows:
        description = row.get("description", "")
        target_ledger = _match_rule(description, rules)

        if target_ledger is None:
            unmatched.append(row)
            continue

        target_path = root / (target_ledger + ".csv")
        if target_path not in existing_hashes:
            existing_hashes[target_path] = {row_hash(r) for r in (read_csv(target_path) if target_path.exists() else [])}

        h = row_hash(row)
        if h in existing_hashes[target_path]:
            matched.append(row)
            continue

        _append_row(row, target_path)
        existing_hashes[target_path].add(h)
        matched.append(row)

    return matched, unmatched


def _match_rule(description: str, rules: dict[str, str]) -> str | None:
    desc_upper = description.upper()
    for pattern, target in rules.items():
        if pattern.upper() in desc_upper:
            return target
    return None


def _append_row(row: dict, target_path: Path) -> None:
    write_header = not target_path.exists() or target_path.stat().st_size == 0
    with open(target_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
