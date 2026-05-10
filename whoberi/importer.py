"""Bank CSV import — match rows to target ledger CSVs via pattern rules."""
import csv
import hashlib
from pathlib import Path


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
    rows = _read_csv(source)
    matched = []
    unmatched = []

    for row in rows:
        description = row.get("description", "")
        target_ledger = _match_rule(description, rules)

        if target_ledger is None:
            unmatched.append(row)
            continue

        target_path = root / (target_ledger + ".csv")
        if _is_duplicate(row, target_path):
            matched.append(row)
            continue

        _append_row(row, target_path)
        matched.append(row)

    return matched, unmatched


def _match_rule(description: str, rules: dict[str, str]) -> str | None:
    desc_upper = description.upper()
    for pattern, target in rules.items():
        if pattern.upper() in desc_upper:
            return target
    return None


def _row_hash(row: dict) -> str:
    key = "|".join(f"{k}={v}" for k, v in sorted(row.items()))
    return hashlib.sha256(key.encode()).hexdigest()


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _is_duplicate(row: dict, target_path: Path) -> bool:
    existing = _read_csv(target_path)
    target_hash = _row_hash(row)
    return any(_row_hash(r) == target_hash for r in existing)


def _append_row(row: dict, target_path: Path) -> None:
    write_header = not target_path.exists() or target_path.stat().st_size == 0
    with open(target_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
