"""Shared loader for handler/reporter Python plugin modules."""
import importlib.util
from pathlib import Path
from types import ModuleType


def load_module(path: Path, kind: str, display: str) -> ModuleType:
    """`display` is the user-facing identifier (e.g. 'expenses/software.py') used
    in error messages and to derive a unique import spec name."""
    slug = display.replace("/", "_").rsplit(".", 1)[0]
    spec = importlib.util.spec_from_file_location(f"_{kind}_{slug}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ValueError(
            f"Failed to load {kind} '{display}': {type(e).__name__}: {e}"
        ) from e
    for name in sorted(n for n in dir(module) if n.startswith("_test_")):
        fn = getattr(module, name)
        if not callable(fn):
            continue
        try:
            fn()
        except Exception as e:
            raise ValueError(
                f"{kind} '{display}' self-test {name} failed: {type(e).__name__}: {e}"
            ) from e
    return module
