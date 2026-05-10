import tomllib
from pathlib import Path


def load_config(root: Path) -> dict:
    config_path = root / "config.toml"
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def load_overrides(csv_path: Path) -> dict:
    toml_path = csv_path.with_suffix(".toml")
    if not toml_path.exists():
        return {}
    with open(toml_path, "rb") as f:
        return tomllib.load(f)
