import pytest

from whoberi.config import load_config


def test_missing_config_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="config.toml not found"):
        load_config(tmp_path)

_VALID_DIRS = '[dirs]\nledgers = "books"\nimports = "imports"\nreports = "reports"\n'


@pytest.mark.parametrize("toml_content", [
    "[accounts]\nasset = []\n[foo]\nbar = 1\n",
    "bad_key = 1\n",
    'as_of = "2026-01-01"\n',  # no longer a reserved key — belongs under [consts]
])
def test_unknown_top_level_key_raises(tmp_path, toml_content):
    (tmp_path / "config.toml").write_text(toml_content)
    with pytest.raises(ValueError, match="Unknown top-level config key"):
        load_config(tmp_path)


@pytest.mark.parametrize("toml_content", [
    "[accounts]\nasset = []\n",
    "[consts.tax]\nhst_rate = 0.13\n",
])
def test_missing_dirs_raises(tmp_path, toml_content):
    (tmp_path / "config.toml").write_text(toml_content)
    with pytest.raises(ValueError, match=r"\[dirs\]"):
        load_config(tmp_path)


@pytest.mark.parametrize("toml_content", [
    '[dirs]\nledgers = "books"\n',
    '[dirs]\nledgers = "books"\nimports = "i"\nreports = "r"\nbogus = "x"\n',
    '[dirs]\nledgers = 7\nimports = "i"\nreports = "r"\n',
])
def test_dirs_shape_raises(tmp_path, toml_content):
    (tmp_path / "config.toml").write_text(toml_content)
    with pytest.raises(ValueError):
        load_config(tmp_path)


@pytest.mark.parametrize("toml_content", [
    _VALID_DIRS,
    "[accounts]\nasset = []\n" + _VALID_DIRS,
    "[consts.tax]\nhst_rate = 0.13\n" + _VALID_DIRS,
    "[accounts]\nasset = []\n\n[consts.tax]\nhst_rate = 0.13\n" + _VALID_DIRS,
])
def test_valid_config_accepted(tmp_path, toml_content):
    (tmp_path / "config.toml").write_text(toml_content)
    config = load_config(tmp_path)
    assert isinstance(config, dict)


@pytest.mark.parametrize("toml_content,match", [
    ('consts = "string"\n' + _VALID_DIRS, r"\[consts\] must be a table"),
])
def test_invalid_optional_keys_raise(tmp_path, toml_content, match):
    (tmp_path / "config.toml").write_text(toml_content)
    with pytest.raises(ValueError, match=match):
        load_config(tmp_path)
