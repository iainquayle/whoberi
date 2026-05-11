import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from whoberi.report_context import ReportContext


@dataclass(frozen=True)
class ReportDef:
    name: str
    description: str
    fn: Callable[[ReportContext], str]
    source: str  # "built-in" or file path string


def load_plugins(reports_dir: Path) -> dict[str, ReportDef]:
    if not reports_dir.is_dir():
        return {}
    plugins: dict[str, ReportDef] = {}
    for path in sorted(reports_dir.glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"_report_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for attr in ("NAME", "DESCRIPTION", "report"):
            if not hasattr(mod, attr):
                raise ValueError(f"{path}: missing required attribute '{attr}'")
        name = mod.NAME
        if name in plugins:
            raise ValueError(
                f"Duplicate report name '{name}': {plugins[name].source} and {path}"
            )
        plugins[name] = ReportDef(
            name=name,
            description=mod.DESCRIPTION,
            fn=mod.report,
            source=str(path),
        )
    return plugins


def build_registry(
    builtin: dict[str, ReportDef], custom: dict[str, ReportDef]
) -> dict[str, ReportDef]:
    conflicts = set(builtin) & set(custom)
    if conflicts:
        names = ", ".join(sorted(conflicts))
        raise ValueError(f"Custom report(s) conflict with built-in names: {names}")
    return {**builtin, **custom}
