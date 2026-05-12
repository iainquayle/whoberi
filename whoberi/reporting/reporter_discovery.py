import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from whoberi.reporting.reporter_context import ReporterContext


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
        spec = importlib.util.spec_from_file_location(f"_reporter_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            raise ValueError(
                f"Failed to load reporter '{path.name}': {type(e).__name__}: {e}"
            ) from e
        for attr in ("NAME", "DESCRIPTION", "report"):
            if not hasattr(mod, attr):
                raise ValueError(f"{path}: missing required attribute '{attr}'")
        name = mod.NAME
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
