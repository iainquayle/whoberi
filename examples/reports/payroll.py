from decimal import Decimal

NAME = "payroll"
DESCRIPTION = "Payroll summary"


def report(ctx) -> str:
    salary = ctx.combined.get("salary", Decimal("0"))
    tax = ctx.combined.get("cra-tax", Decimal("0"))
    cpp = ctx.combined.get("cra-cpp", Decimal("0"))
    ei = ctx.combined.get("cra-ei", Decimal("0"))
    return ctx.render(
        [
            ("Gross salary", salary),
            ("Income tax", tax),
            ("CPP", cpp),
            ("EI", ei),
        ],
        title=f"Payroll{ctx.period_suffix}",
    )
