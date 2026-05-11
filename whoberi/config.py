import tomllib
from pathlib import Path


def load_config(root: Path) -> dict:
    config_path = root / "config.toml"
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as f:
        return tomllib.load(f)
