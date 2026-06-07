"""Verifies the loader runs `_test_*` functions and halts on failure."""
import pytest

from whoberi._plugin import load_module


CASES = [
    ("good.py", "def _test_ok():\n    assert 1 + 1 == 2\n", None),
    (
        "bad.py",
        "def _test_bad():\n    assert False, 'nope'\n",
        ("bad.py", "_test_bad", "AssertionError"),
    ),
    ("weird.py", "_test_value = 5\n", None),
]


@pytest.mark.parametrize(
    "name,body,expect_fail",
    CASES,
    ids=["passing-test", "failing-test", "non-callable-attr"],
)
def test_loader_self_test_handling(tmp_path, name, body, expect_fail):
    path = tmp_path / name
    path.write_text(body)
    if expect_fail is None:
        load_module(path, "handler", name)
        return
    with pytest.raises(ValueError) as exc:
        load_module(path, "handler", name)
    msg = str(exc.value)
    for fragment in expect_fail:
        assert fragment in msg, f"missing {fragment!r} in {msg!r}"
