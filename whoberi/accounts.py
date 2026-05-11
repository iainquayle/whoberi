from enum import StrEnum


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


_KNOWN_TYPES = {t.value for t in AccountType}


class AccountRegistry:
    def __init__(self, explicit: dict[AccountType, set[str]]):
        self._explicit = explicit
        self._by_name: dict[str, AccountType] = {
            name: t for t, names in explicit.items() for name in names
        }

    def type_of(self, name: str) -> AccountType:
        if name not in self._by_name:
            raise KeyError(f"Unknown account '{name}' — add it to [accounts] in config.toml")
        return self._by_name[name]

    def is_known(self, name: str) -> bool:
        return name in self._by_name

    def names_of(self, t: AccountType) -> list[str]:
        return sorted(self._explicit.get(t, set()))


def load_registry(config: dict) -> AccountRegistry:
    section = config.get("accounts")
    if not section:
        raise ValueError(
            "Missing or empty [accounts] section in config.toml — "
            f"must declare at least one type. Valid types: {sorted(_KNOWN_TYPES)}"
        )

    errors: list[str] = []
    seen: dict[str, str] = {}   # name -> first type that claimed it
    explicit: dict[AccountType, set[str]] = {}

    for key, value in section.items():
        if key not in _KNOWN_TYPES:
            errors.append(
                f"Unknown account type '{key}' in [accounts] — "
                f"valid types: {sorted(_KNOWN_TYPES)}"
            )
            continue
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(
                f"[accounts].{key} must be a list of strings, got {type(value).__name__}"
            )
            continue
        t = AccountType(key)
        names: set[str] = set()
        for name in value:
            if name in seen:
                errors.append(
                    f"Duplicate account '{name}': appears in both '{seen[name]}' and '{key}'"
                )
            else:
                seen[name] = key
                names.add(name)
        explicit[t] = names

    if errors:
        raise ValueError("\n".join(errors))

    return AccountRegistry(explicit)
