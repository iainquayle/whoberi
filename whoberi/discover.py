import csv
import importlib.util
from pathlib import Path
from types import ModuleType

from whoberi.types import LedgerMeta

_SKIP_DIRS = {"imports", "reports"}


def discover(root: Path) -> list[tuple[Path, ModuleType, LedgerMeta]]:
    csvs, pys = _collect(root)
    errors = []
    for csv_path in sorted(csvs):
        if csv_path.with_suffix(".py") not in pys:
            errors.append(
                f"Missing handler: expected {csv_path.with_suffix('.py').relative_to(root)}"
                f" for {csv_path.relative_to(root)}"
            )
    for py_path in sorted(pys):
        if py_path.with_suffix(".csv") not in csvs:
            errors.append(f"Orphan handler: {py_path.relative_to(root)} has no matching CSV")
    if errors:
        raise FileNotFoundError("\n".join(errors))
    return [
        (
            csv_path,
            _load_handler(csv_path, root),
            LedgerMeta(name=csv_path.stem, directory=csv_path.parent.name, path=csv_path),
        )
        for csv_path in sorted(csvs)
    ]


def _collect(root: Path) -> tuple[set[Path], set[Path]]:
    csvs: set[Path] = set()
    pys: set[Path] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix == ".csv":
            csvs.add(path)
        elif path.suffix == ".py":
            pys.add(path)
    return csvs, pys


def _load_handler(csv_path: Path, root: Path) -> ModuleType:
    handler_path = csv_path.with_suffix(".py")
    slug = csv_path.relative_to(root).with_suffix("").as_posix().replace("/", "_")
    spec = importlib.util.spec_from_file_location(f"_handler_{slug}", handler_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))
