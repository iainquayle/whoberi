from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from whoberi._plugin import load_module
from whoberi.reporting.reporter_context import ReporterContext

RESERVED_REPORT_NAMES = {"list", "all"}


@dataclass(frozen=True)
class ReporterDef:
    name: str
    description: str
    fn: Callable[[ReporterContext], str]
    source: str  # "built-in" or file path string


def load_reporters(reports_dir: Path) -> dict[str, ReporterDef]:
    if not reports_dir.is_dir():
        return {}
    plugins: dict[str, ReporterDef] = {}
    for path in sorted(reports_dir.glob("*.py")):
        mod = load_module(path, "reporter", path.name)
        for attr in ("NAME", "DESCRIPTION", "report"):
            if not hasattr(mod, attr):
                raise ValueError(f"{path}: missing required attribute '{attr}'")
        name = mod.NAME
        if not isinstance(name, str):
            raise ValueError(f"{path}: NAME must be a string, got {type(name).__name__}")
        if not isinstance(mod.DESCRIPTION, str):
            raise ValueError(
                f"{path}: DESCRIPTION must be a string, got {type(mod.DESCRIPTION).__name__}"
            )
        if not callable(mod.report):
            raise ValueError(f"{path}: report must be callable, got {type(mod.report).__name__}")
        if name in RESERVED_REPORT_NAMES:
            raise ValueError(
                f"{path}: NAME '{name}' is reserved (used as a CLI sentinel by `report list` / `report all`)"
            )
        if name in plugins:
            raise ValueError(
                f"Duplicate report name '{name}': {plugins[name].source} and {path}"
            )
        plugins[name] = ReporterDef(
            name=name,
            description=mod.DESCRIPTION,
            fn=mod.report,
            source=str(path),
        )
    return plugins


def build_reporter_registry(
    builtin: dict[str, ReporterDef], custom: dict[str, ReporterDef]
) -> dict[str, ReporterDef]:
    conflicts = set(builtin) & set(custom)
    if conflicts:
        names = ", ".join(sorted(conflicts))
        raise ValueError(f"Custom report(s) conflict with built-in names: {names}")
    return {**builtin, **custom}
