from decimal import Decimal, ROUND_HALF_UP

_DEFAULT_HST = Decimal("0.13")
_CENT = Decimal("0.01")


def split_hst(total: Decimal, config: dict) -> tuple[Decimal, Decimal]:
    """Return (pretax, hst) from an HST-inclusive total."""
    rate = Decimal(str(config.get("tax", {}).get("hst_rate", _DEFAULT_HST)))
    hst = (total * rate / (1 + rate)).quantize(_CENT, ROUND_HALF_UP)
    return total - hst, hst
