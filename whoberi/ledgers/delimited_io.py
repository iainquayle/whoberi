"""Delimited-file read/write edge functions — IO only, no transformation.

Supports CSV (.csv), TSV (.tsv, tab-delimited), and PSV (.psv, pipe-delimited).
Delimiter is selected by file extension; unknown extensions raise ValueError.
"""
import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

DELIMITERS = {".csv": ",", ".tsv": "\t", ".psv": "|"}


def _delimiter(path: Path) -> str:
    try:
        return DELIMITERS[path.suffix]
    except KeyError:
        raise ValueError(
            f"{path}: unsupported ledger extension '{path.suffix}'"
            f" (expected one of {sorted(DELIMITERS)})"
        )


def read_rows(path: Path) -> Iterator[dict]:
    with open(path, newline="") as f:
        yield from csv.DictReader(f, delimiter=_delimiter(path))


def read_headers(path: Path) -> list[str]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter=_delimiter(path)).fieldnames or [])


def read_rows_with_headers(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=_delimiter(path))
        return list(reader.fieldnames or []), list(reader)


def write_rows(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=_delimiter(path))
        writer.writeheader()
        writer.writerows(rows)


def resolve_existing(root: Path, stem: str) -> Path | None:
    """Find `root/stem.<ext>` for any supported extension.

    Returns the path if exactly one matches, None if none exist.
    Raises ValueError if multiple supported-extension files share the stem.
    """
    existing = [root / f"{stem}{s}" for s in DELIMITERS]
    existing = [p for p in existing if p.exists()]
    if len(existing) > 1:
        names = ", ".join(p.name for p in existing)
        raise ValueError(f"Ambiguous ledger '{stem}': multiple files exist ({names})")
    return existing[0] if existing else None
