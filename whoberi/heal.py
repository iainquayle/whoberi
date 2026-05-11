"""Auto-heal ledger CSVs: sort chronologically, remove duplicate rows."""
import csv
from pathlib import Path

from whoberi.hashing import row_hash


def heal_csv(path: Path) -> list[str]:
    """
    Sort rows by date and remove duplicate rows (by full-row hash) in-place.
    Returns a list of log messages describing changes made; empty if nothing changed.
    """
    if not path.exists():
        return []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        headers = list(reader.fieldnames)
        rows = list(reader)

    if not rows:
        return []

    logs = []

    # Deduplicate — keep first occurrence by full-row hash
    seen: set[str] = set()
    deduped = []
    for row in rows:
        h = row_hash(row)
        if h in seen:
            logs.append(f"heal: removed duplicate row in {path.name}: {dict(row)}")
        else:
            seen.add(h)
            deduped.append(row)

    # Sort chronologically by date column
    try:
        sorted_rows = sorted(deduped, key=lambda r: r.get("date", ""))
    except Exception:
        sorted_rows = deduped

    if sorted_rows != deduped:
        logs.append(f"heal: re-sorted {path.name} chronologically ({len(sorted_rows)} rows)")

    if not logs:
        return []

    # Rewrite in-place
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(sorted_rows)

    return logs


