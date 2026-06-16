from pathlib import Path
from types import ModuleType

from whoberi._plugin import load_module
from whoberi.ledgers.delimited_io import DELIMITERS
from whoberi.types import LedgerMeta

LEDGER_SUFFIXES = frozenset(DELIMITERS)


def discover(ledgers_root: Path) -> list[tuple[Path, ModuleType, LedgerMeta]]:
    ledgers, pys = _collect(ledgers_root)
    ledger_pys = {p.with_suffix(".py") for p in ledgers}
    errors = []
    for ledger_path in sorted(ledgers):
        if ledger_path.with_suffix(".py") not in pys:
            errors.append(
                f"Missing handler: expected {ledger_path.with_suffix('.py').relative_to(ledgers_root)}"
                f" for {ledger_path.relative_to(ledgers_root)}"
            )
    for py_path in sorted(pys):
        if py_path not in ledger_pys:
            errors.append(
                f"Orphan handler: {py_path.relative_to(ledgers_root)} has no matching ledger"
            )
    if errors:
        summary = f"{len(errors)} handler pairing error(s):"
        raise ValueError("\n".join([summary, *(f"  - {e}" for e in errors)]))
    return [
        (
            ledger_path,
            _load_handler(ledger_path, ledgers_root),
            LedgerMeta(name=ledger_path.stem, directory=ledger_path.parent.name, path=ledger_path),
        )
        for ledger_path in sorted(ledgers)
    ]


def _collect(ledgers_root: Path) -> tuple[set[Path], set[Path]]:
    ledgers: set[Path] = set()
    pys: set[Path] = set()
    by_stem: dict[Path, list[Path]] = {}
    for path in ledgers_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in LEDGER_SUFFIXES:
            ledgers.add(path)
            by_stem.setdefault(path.with_suffix(""), []).append(path)
        elif path.suffix == ".py":
            pys.add(path)
    ambiguous = [paths for paths in by_stem.values() if len(paths) > 1]
    if ambiguous:
        details = [
            f"  - {', '.join(str(p.relative_to(ledgers_root)) for p in sorted(paths))}"
            for paths in ambiguous
        ]
        raise ValueError(
            "\n".join(["Ambiguous ledger files (same stem, multiple formats):", *details])
        )
    return ledgers, pys


def _load_handler(ledger_path: Path, ledgers_root: Path) -> ModuleType:
    handler_path = ledger_path.with_suffix(".py")
    rel = handler_path.relative_to(ledgers_root).as_posix()
    return load_module(handler_path, "handler", rel)
