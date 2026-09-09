"""Shared plugin discovery — one table covers reporters and document generators."""
import pytest

from whoberi.documents.document_discovery import DOCUMENT_SPEC
from whoberi.plugins import PluginDef, build_registry, load_plugins
from whoberi.reporting.reporter_discovery import REPORTER_SPEC

SPECS = [REPORTER_SPEC, DOCUMENT_SPEC]


def _write(tmp_path, source: str, name: str = "bad.py"):
    directory = tmp_path / "plugins"
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(source)
    return directory


def _valid(spec, name: str = "x") -> str:
    return f'NAME = "{name}"\nDESCRIPTION = "x"\ndef {spec.entrypoint}(ctx): return ""\n'


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.kind)
def test_missing_directory_returns_empty(tmp_path, spec):
    assert load_plugins(tmp_path / "nonexistent", spec) == {}


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.kind)
def test_missing_attribute_raises(tmp_path, spec):
    with pytest.raises(ValueError, match="missing required attribute"):
        load_plugins(_write(tmp_path, 'NAME = "bad"\n'), spec)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.kind)
def test_syntax_error_names_the_kind(tmp_path, spec):
    with pytest.raises(ValueError, match=f"Failed to load {spec.kind} 'bad.py'"):
        load_plugins(_write(tmp_path, "this is not python!!!\n"), spec)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.kind)
@pytest.mark.parametrize("reserved", ["list", "all"])
def test_reserved_name_raises(tmp_path, spec, reserved):
    with pytest.raises(ValueError, match="reserved"):
        load_plugins(_write(tmp_path, _valid(spec, reserved)), spec)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.kind)
@pytest.mark.parametrize("mutate,match", [
    (lambda src, spec: src.replace('NAME = "x"', "NAME = 42"), "NAME must be a string"),
    (lambda src, spec: src.replace('DESCRIPTION = "x"', "DESCRIPTION = 42"), "DESCRIPTION must be a string"),
    (lambda src, spec: f'NAME = "x"\nDESCRIPTION = "x"\n{spec.entrypoint} = 42\n', "must be callable"),
])
def test_attribute_type_checks(tmp_path, spec, mutate, match):
    with pytest.raises(ValueError, match=match):
        load_plugins(_write(tmp_path, mutate(_valid(spec), spec)), spec)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.kind)
def test_duplicate_name_raises(tmp_path, spec):
    directory = _write(tmp_path, _valid(spec), name="a.py")
    _write(tmp_path, _valid(spec), name="b.py")
    with pytest.raises(ValueError, match=f"Duplicate {spec.kind} name 'x'"):
        load_plugins(directory, spec)


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.kind)
def test_failing_self_test_raises(tmp_path, spec):
    source = _valid(spec) + "def _test_boom(): assert False\n"
    with pytest.raises(ValueError, match="self-test _test_boom failed"):
        load_plugins(_write(tmp_path, source), spec)


def test_builtin_conflict_raises():
    shared = {"pnl": PluginDef(name="pnl", description="x", fn=lambda ctx: "", source="built-in")}
    with pytest.raises(ValueError, match="Custom reporter\\(s\\) conflict with built-in"):
        build_registry(shared, shared, "reporter")
