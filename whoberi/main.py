import argparse
import csv as csv_module
import sys
from decimal import Decimal
from pathlib import Path

from whoberi.aggregate import aggregate, check_balance
from whoberi.config import load_config
from whoberi.discover import discover, read_csv
from whoberi.heal import heal_csv
from whoberi.reports import report_balance, report_gst, report_payroll, report_pnl
from whoberi.types import Entry
from whoberi.validate import validate_entries


def run_pipeline(root: Path) -> tuple[list[Entry], dict[str, Decimal]]:
    config = load_config(root)
    ledgers = discover(root, config)
    entries = []
    for csv_path, handler, meta in ledgers:
        for msg in heal_csv(csv_path):
            print(msg, file=sys.stderr)
        rows = read_csv(csv_path)
        ledger_key = str(csv_path.relative_to(root).with_suffix(""))
        for entry in handler.process(rows, config, meta):
            entry.meta.setdefault("ledger", ledger_key)
            entries.append(entry)
    combined = aggregate(entries)
    return entries, combined


def cmd_discover(root: Path, _args) -> int:
    config = load_config(root)
    ledgers = discover(root, config)
    if not ledgers:
        print("No ledgers found.")
        return 0
    print(f"{'CSV':<40} {'Handler':<40} {'Overrides'}")
    print("─" * 90)
    for csv_path, handler, meta in ledgers:
        overrides = ", ".join(f"{k}={v}" for k, v in meta.overrides.items()) or "—"
        print(f"{str(csv_path.relative_to(root)):<40} {str(Path(handler.__file__).relative_to(root)):<40} {overrides}")
    return 0


def cmd_validate(root: Path, _args) -> int:
    config = load_config(root)
    entries, _ = run_pipeline(root)
    account_names = config.get("accounts", {}).get("names")
    errors = validate_entries(entries, account_names)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print(f"OK — {len(entries)} entries, all balanced.")
    return 0


def cmd_accounts(root: Path, _args) -> int:
    _, combined = run_pipeline(root)
    if not combined:
        print("No accounts.")
        return 0
    width = max(len(k) for k in combined)
    for account in sorted(combined):
        print(f"  {account:<{width}}  {combined[account]:>12.2f}")
    off = check_balance(combined)
    print(f"\n  {'Balance check':<{width}}  {off:>12.2f}")
    return 0


def cmd_status(root: Path, _args) -> int:
    _, combined = run_pipeline(root)

    cash = combined.get("assets:venn-cad", Decimal("0"))
    gst_collected = -combined.get("tax:hst-collected", Decimal("0"))
    gst_paid = combined.get("tax:hst-paid", Decimal("0"))
    gst_owing = gst_collected - gst_paid

    print(f"  Cash (venn-cad):  {cash:>12.2f}")
    print(f"  GST/HST owing:    {gst_owing:>12.2f}")
    return 0


def cmd_report(root: Path, args) -> int:
    entries, _ = run_pipeline(root)
    period = getattr(args, "period", None)

    report_type = args.type
    if report_type == "pnl":
        print(report_pnl(entries, period))
    elif report_type == "gst":
        print(report_gst(entries, period))
    elif report_type == "payroll":
        print(report_payroll(entries, period))
    elif report_type == "balance":
        print(report_balance(entries, period))
    elif report_type == "annual":
        for fn in (report_pnl, report_gst, report_payroll, report_balance):
            print(fn(entries, period))
            print()
    else:
        print(f"Unknown report type: {report_type}", file=sys.stderr)
        return 1
    return 0


def cmd_add(root: Path, args) -> int:
    ledger_path = root / (args.ledger + ".csv")
    if not ledger_path.exists():
        print(f"Ledger not found: {ledger_path}", file=sys.stderr)
        return 1
    with open(ledger_path, "a", newline="") as f:
        writer = csv_module.writer(f)
        writer.writerow(args.fields)
    print(f"Added row to {ledger_path.relative_to(root)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whoberi",
        description="Plugin-based accounting CLI",
    )
    parser.add_argument(
        "--root", type=Path, default=Path("."),
        help="Data directory root (default: current directory)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("discover", help="List detected CSVs and resolved handlers")
    sub.add_parser("validate", help="Run all validation checks")
    sub.add_parser("accounts", help="Print combined account balances")
    sub.add_parser("status", help="Quick summary: cash, GST owing")

    report_p = sub.add_parser("report", help="Generate financial reports")
    report_p.add_argument("type", choices=["pnl", "gst", "payroll", "balance", "annual"])
    report_p.add_argument("--period", help="Period: Q1, Q1 2026, 2026-01, 2026")

    add_p = sub.add_parser("add", help="Append a row to a ledger CSV")
    add_p.add_argument("ledger", help="Ledger path relative to root (without .csv)")
    add_p.add_argument("fields", nargs="+", help="Field values to append")

    return parser


def cli() -> None:
    parser = build_parser()
    args = parser.parse_args()
    root = args.root.resolve()

    if not root.is_dir():
        print(f"ERROR: Root directory not found: {root}", file=sys.stderr)
        sys.exit(1)

    commands = {
        "discover": cmd_discover,
        "validate": cmd_validate,
        "accounts": cmd_accounts,
        "status": cmd_status,
        "report": cmd_report,
        "add": cmd_add,
    }

    sys.exit(commands[args.command](root, args))


if __name__ == "__main__":
    cli()
