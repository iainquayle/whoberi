from pathlib import Path

from whoberi.plugins import PluginDef, PluginSpec, load_plugins

DOCUMENT_SPEC = PluginSpec(
    kind="document",
    command="document",
    entrypoint="generate",
    reserved=frozenset({"list", "all"}),
)


def load_generators(generators_dir: Path) -> dict[str, PluginDef]:
    return load_plugins(generators_dir, DOCUMENT_SPEC)
