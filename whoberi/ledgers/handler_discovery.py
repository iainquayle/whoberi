import importlib.util
from pathlib import Path
from types import ModuleType

from whoberi.types import LedgerMeta


def discover(ledgers_root: Path) -> list[tuple[Path, ModuleType, LedgerMeta]]:
    csvs, pys = _collect(ledgers_root)
    errors = []
    for csv_path in sorted(csvs):
        if csv_path.with_suffix(".py") not in pys:
            errors.append(
                f"Missing handler: expected {csv_path.with_suffix('.py').relative_to(ledgers_root)}"
                f" for {csv_path.relative_to(ledgers_root)}"
            )
    for py_path in sorted(pys):
        if py_path.with_suffix(".csv") not in csvs:
            errors.append(f"Orphan handler: {py_path.relative_to(ledgers_root)} has no matching CSV")
    if errors:
        summary = f"{len(errors)} handler pairing error(s):"
        raise ValueError("\n".join([summary, *(f"  - {e}" for e in errors)]))
    return [
        (
            csv_path,
            _load_handler(csv_path, ledgers_root),
            LedgerMeta(name=csv_path.stem, directory=csv_path.parent.name, path=csv_path),
        )
        for csv_path in sorted(csvs)
    ]


def _collect(ledgers_root: Path) -> tuple[set[Path], set[Path]]:
    csvs: set[Path] = set()
    pys: set[Path] = set()
    for path in ledgers_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".csv":
            csvs.add(path)
        elif path.suffix == ".py":
            pys.add(path)
    return csvs, pys


def _load_handler(csv_path: Path, ledgers_root: Path) -> ModuleType:
    handler_path = csv_path.with_suffix(".py")
    slug = csv_path.relative_to(ledgers_root).with_suffix("").as_posix().replace("/", "_")
    spec = importlib.util.spec_from_file_location(f"_handler_{slug}", handler_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        rel = handler_path.relative_to(ledgers_root)
        raise ValueError(f"Failed to load handler '{rel}': {type(e).__name__}: {e}") from e
    return module
