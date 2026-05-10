import csv
import importlib.util
import re
from pathlib import Path
from types import ModuleType

from whoberi.config import load_overrides
from whoberi.types import LedgerMeta

_SKIP_DIRS = {"imports", "reports"}
_COLUMN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def discover(root: Path, config: dict | None = None) -> list[tuple[Path, ModuleType, LedgerMeta]]:
    """Find all CSVs under root, resolve their handlers, build LedgerMeta."""
    column_pattern = (config or {}).get("column_name_pattern", _COLUMN_NAME_RE.pattern)
    col_re = re.compile(column_pattern)

    handler_cache: dict[Path, ModuleType] = {}
    results = []

    for csv_path in sorted(root.rglob("*.csv")):
        # Skip ignored directories
        if any(part in _SKIP_DIRS for part in csv_path.parts):
            continue

        handler = _resolve_handler(csv_path.parent, root, handler_cache)
        if handler is None:
            raise FileNotFoundError(
                f"No handler.py found for {csv_path} (searched up to {root})"
            )

        meta = LedgerMeta(
            name=csv_path.stem,
            directory=csv_path.parent.name,
            path=csv_path,
            overrides=load_overrides(csv_path),
        )
        results.append((csv_path, handler, meta))

    return results


def _resolve_handler(directory: Path, root: Path, cache: dict[Path, ModuleType]) -> ModuleType | None:
    """Walk upward from directory to root, return nearest handler module."""
    current = directory
    while True:
        if current in cache:
            return cache[current]

        handler_path = current / "handler.py"
        if handler_path.exists():
            module = _load_handler(handler_path)
            cache[current] = module
            return module

        if current == root:
            return None
        current = current.parent


def _load_handler(handler_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"_handler_{handler_path.parent.name}", handler_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(csv_path: Path) -> csv.DictReader:
    return csv.DictReader(open(csv_path, newline=""))
