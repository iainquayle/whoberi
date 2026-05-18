import tomllib
from datetime import date
from pathlib import Path

_ALLOWED_KEYS = {"accounts", "as_of", "consts", "dirs"}
_DIRS_KEYS = {"ledgers", "imports", "reports"}


def load_config(root: Path) -> dict:
    config_path = root / "config.toml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.toml not found at {config_path}")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)
    unknown = set(config) - _ALLOWED_KEYS
    if unknown:
        allowed = ", ".join(sorted(_ALLOWED_KEYS))
        raise ValueError(f"Unknown top-level config key(s): {', '.join(sorted(unknown))}. Allowed: {allowed}")
    dirs = config.get("dirs")
    if dirs is None:
        raise ValueError("[dirs] is required in config.toml")
    missing = _DIRS_KEYS - set(dirs)
    if missing:
        raise ValueError(f"[dirs] missing required keys: {', '.join(sorted(missing))}")
    extra = set(dirs) - _DIRS_KEYS
    if extra:
        raise ValueError(f"[dirs] unknown keys: {', '.join(sorted(extra))}")
    for k in _DIRS_KEYS:
        if not isinstance(dirs[k], str):
            raise ValueError(f"[dirs].{k} must be a string, got {type(dirs[k]).__name__}")
    if "as_of" in config:
        as_of = config["as_of"]
        if not isinstance(as_of, str):
            raise ValueError(f"as_of must be an ISO date string (YYYY-MM-DD), got {type(as_of).__name__}")
        try:
            date.fromisoformat(as_of)
        except ValueError as e:
            raise ValueError(f"as_of is not a valid ISO date: {as_of!r} ({e})") from e
    if "consts" in config and not isinstance(config["consts"], dict):
        raise ValueError(f"[consts] must be a table, got {type(config['consts']).__name__}")
    return config
