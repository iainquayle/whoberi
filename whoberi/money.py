from decimal import Decimal


def fmt_money(amount: Decimal) -> str:
    if amount < 0:
        return f"$({-amount:,.2f})"
    return f"${amount:,.2f}"
