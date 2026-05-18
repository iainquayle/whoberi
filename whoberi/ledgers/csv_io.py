"""CSV read/write edge functions — IO only, no transformation."""
import csv
from collections.abc import Iterable, Iterator
from pathlib import Path


def read_csv(path: Path) -> Iterator[dict]:
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
