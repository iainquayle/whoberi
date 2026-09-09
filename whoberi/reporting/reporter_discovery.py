from pathlib import Path

from whoberi.plugins import PluginDef, PluginSpec, build_registry, load_plugins

REPORTER_SPEC = PluginSpec(
    kind="reporter",
    command="report",
    entrypoint="report",
    reserved=frozenset({"list", "all"}),
)

ReporterDef = PluginDef


def load_reporters(reports_dir: Path) -> dict[str, PluginDef]:
    return load_plugins(reports_dir, REPORTER_SPEC)


def build_reporter_registry(
    builtin: dict[str, PluginDef], custom: dict[str, PluginDef]
) -> dict[str, PluginDef]:
    return build_registry(builtin, custom, REPORTER_SPEC.kind)
