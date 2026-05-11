import pytest

from whoberi.accounts import AccountRegistry, AccountType, load_registry
from tests.conftest import make_registry as _registry


# --- type_of ---

def test_type_of_known_name():
    reg = _registry(asset=["venn-cad"], income=["fooco"])
    assert reg.type_of("venn-cad") == AccountType.ASSET
    assert reg.type_of("fooco") == AccountType.INCOME


def test_type_of_unknown_raises():
    reg = _registry(asset=["venn-cad"])
    with pytest.raises(KeyError, match="Unknown account 'typo'"):
        reg.type_of("typo")


def test_is_known():
    reg = _registry(asset=["venn-cad"])
    assert reg.is_known("venn-cad")
    assert not reg.is_known("ghost")


# --- load_registry ---

def test_load_registry_valid():
    config = {"accounts": {"asset": ["venn-cad"], "income": ["fooco"]}}
    reg = load_registry(config)
    assert reg.type_of("venn-cad") == AccountType.ASSET
    assert reg.type_of("fooco") == AccountType.INCOME


def test_load_registry_missing_section():
    with pytest.raises(ValueError, match="Missing or empty"):
        load_registry({})


def test_load_registry_empty_section():
    with pytest.raises(ValueError, match="Missing or empty"):
        load_registry({"accounts": {}})


@pytest.mark.parametrize("bad_key", ["asssets", "tax"])
def test_load_registry_unknown_type_key(bad_key):
    config = {"accounts": {bad_key: ["venn-cad"]}}
    with pytest.raises(ValueError, match=f"Unknown account type '{bad_key}'"):
        load_registry(config)


@pytest.mark.parametrize("bad_value", [
    "venn-cad",
    {"name": "venn-cad"},
    42,
])
def test_load_registry_non_list_value(bad_value):
    config = {"accounts": {"asset": bad_value}}
    with pytest.raises(ValueError, match="must be a list of strings"):
        load_registry(config)


def test_load_registry_duplicate_across_types():
    config = {"accounts": {"asset": ["venn-cad"], "expense": ["venn-cad", "software"]}}
    with pytest.raises(ValueError, match="Duplicate account 'venn-cad'"):
        load_registry(config)


def test_load_registry_multiple_duplicates_reported_together():
    config = {"accounts": {"asset": ["a", "b"], "expense": ["a", "b", "c"]}}
    with pytest.raises(ValueError) as exc_info:
        load_registry(config)
    msg = str(exc_info.value)
    assert "'a'" in msg
    assert "'b'" in msg


def test_load_registry_empty_list_valid():
    config = {"accounts": {"asset": [], "income": ["fooco"]}}
    reg = load_registry(config)
    assert reg.is_known("fooco")
    assert not reg.is_known("venn-cad")
