"""CSV read/write edge functions — IO only, no transformation."""
import csv
from collections.abc import Iterable, Iterator
from pathlib import Path


def read_csv(path: Path) -> Iterator[dict]:
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def read_csv_headers(path: Path) -> list[str]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f).fieldnames or [])


def read_csv_with_headers(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
