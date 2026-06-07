"""Verifies the loader runs `_test_*` functions and halts on failure."""
import pytest

from whoberi._plugin import load_module


def _write(tmp_path, name: str, body: str):
    path = tmp_path / name
    path.write_text(body)
    return path


def test_passing_self_test_loads(tmp_path):
    path = _write(tmp_path, "good.py", "def _test_ok():\n    assert 1 + 1 == 2\n")
    mod = load_module(path, "handler", "good.py")
    assert hasattr(mod, "_test_ok")


def test_failing_self_test_halts(tmp_path):
    path = _write(
        tmp_path,
        "bad.py",
        "def _test_bad():\n    assert False, 'nope'\n",
    )
    with pytest.raises(ValueError) as exc:
        load_module(path, "handler", "bad.py")
    msg = str(exc.value)
    assert "bad.py" in msg
    assert "_test_bad" in msg
    assert "AssertionError" in msg


def test_non_callable_test_attr_ignored(tmp_path):
    path = _write(tmp_path, "weird.py", "_test_value = 5\n")
    mod = load_module(path, "reporter", "weird.py")
    assert mod._test_value == 5
