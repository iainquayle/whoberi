"""Discovery and validation shared by reporter and document-generator plugins."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from whoberi._plugin import load_module


@dataclass(frozen=True)
class PluginSpec:
    kind: str                  # "reporter" | "document"
    command: str               # CLI subcommand: "report" | "document"
    entrypoint: str            # module attribute holding the callable: "report" | "generate"
    reserved: frozenset[str]


@dataclass(frozen=True)
class PluginDef:
    name: str
    description: str
    fn: Callable
    source: str  # "built-in" or file path string


def load_plugins(directory: Path, spec: PluginSpec) -> dict[str, PluginDef]:
    if not directory.is_dir():
        return {}
    plugins: dict[str, PluginDef] = {}
    for path in sorted(directory.glob("*.py")):
        plugin = _load_plugin(path, spec)
        if plugin.name in plugins:
            raise ValueError(
                f"Duplicate {spec.kind} name '{plugin.name}': "
                f"{plugins[plugin.name].source} and {path}"
            )
        plugins[plugin.name] = plugin
    return plugins


def _load_plugin(path: Path, spec: PluginSpec) -> PluginDef:
    mod = load_module(path, spec.kind, path.name)
    for attr in ("NAME", "DESCRIPTION", spec.entrypoint):
        if not hasattr(mod, attr):
            raise ValueError(f"{path}: missing required attribute '{attr}'")
    if not isinstance(mod.NAME, str):
        raise ValueError(f"{path}: NAME must be a string, got {type(mod.NAME).__name__}")
    if not isinstance(mod.DESCRIPTION, str):
        raise ValueError(
            f"{path}: DESCRIPTION must be a string, got {type(mod.DESCRIPTION).__name__}"
        )
    fn = getattr(mod, spec.entrypoint)
    if not callable(fn):
        raise ValueError(f"{path}: {spec.entrypoint} must be callable, got {type(fn).__name__}")
    if mod.NAME in spec.reserved:
        raise ValueError(
            f"{path}: NAME '{mod.NAME}' is reserved (used as a CLI sentinel by "
            f"`{spec.command} list` / `{spec.command} all`)"
        )
    return PluginDef(name=mod.NAME, description=mod.DESCRIPTION, fn=fn, source=str(path))


def build_registry(
    builtin: dict[str, PluginDef], custom: dict[str, PluginDef], kind: str
) -> dict[str, PluginDef]:
    conflicts = set(builtin) & set(custom)
    if conflicts:
        names = ", ".join(sorted(conflicts))
        raise ValueError(f"Custom {kind}(s) conflict with built-in names: {names}")
    return {**builtin, **custom}
