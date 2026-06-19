"""Delimited-file read/write edge functions — IO only, no transformation.

Supports CSV (.csv), TSV (.tsv, tab-delimited), and PSV (.psv, pipe-delimited).
Delimiter is selected by file extension; unknown extensions raise ValueError.
"""
import csv
from collections.abc import Iterable, Iterator
from pathlib import Path

DELIMITERS = {".csv": ",", ".tsv": "\t", ".psv": "|"}


def delimiter_for(path: Path) -> str:
    try:
        return DELIMITERS[path.suffix]
    except KeyError:
        raise ValueError(
            f"{path}: unsupported ledger extension '{path.suffix}'"
            f" (expected one of {sorted(DELIMITERS)})"
        )


def read_rows(path: Path) -> Iterator[dict]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter_for(path))
        _check_header(path, reader.fieldnames)
        yield from reader


def read_headers(path: Path) -> list[str]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter_for(path))
        _check_header(path, reader.fieldnames)
        return list(reader.fieldnames or [])


def read_rows_with_headers(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter_for(path))
        _check_header(path, reader.fieldnames)
        return list(reader.fieldnames or []), list(reader)


def write_rows(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter_for(path))
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


def infer_extension(root: Path) -> str:
    """Pick the dominant supported extension among existing ledgers under `root`.

    Used to pick a format when creating a new ledger so the choice conforms to
    the user's existing files. Ties broken by DELIMITERS declaration order.
    Returns '.csv' when no supported files are found.
    """
    counts = {ext: 0 for ext in DELIMITERS}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in DELIMITERS:
            counts[p.suffix] += 1
    if all(c == 0 for c in counts.values()):
        return ".csv"
    order = list(DELIMITERS)
    return max(counts, key=lambda ext: (counts[ext], -order.index(ext)))


def _check_header(path: Path, fieldnames: Iterable[str] | None) -> None:
    """Surface a clear error when a file's content does not match its extension.

    csv.DictReader silently parses a wrong-delimiter file as a single column;
    the giveaway is that the sole header field contains another supported
    delimiter. We raise here so the user sees the format mismatch directly
    rather than a confusing downstream KeyError.
    """
    fields = list(fieldnames or [])
    if len(fields) != 1:
        return
    declared = DELIMITERS[path.suffix]
    for ext, delim in DELIMITERS.items():
        if delim != declared and delim in fields[0]:
            raise ValueError(
                f"{path}: header parsed as a single column but contains '{ext}' "
                f"delimiter — wrong extension for this file?"
            )
