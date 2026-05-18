from decimal import Decimal

NAME = "gst"
DESCRIPTION = "GST/HST collected vs. paid"


def report(ctx) -> str:
    collected = -ctx.combined.get("hst-collected", Decimal("0"))
    paid = ctx.combined.get("hst-paid", Decimal("0"))
    return ctx.render(
        [
            ("Collected", collected),
            ("Paid (ITC)", paid),
            None,
            ("Net owing", collected - paid),
        ],
        title=f"GST/HST{ctx.period_suffix}",
    )
