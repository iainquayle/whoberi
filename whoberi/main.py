import argparse
import csv as csv_module
import sys
from decimal import Decimal
from pathlib import Path

from whoberi.accounts import AccountRegistry, AccountType, load_registry
from whoberi.aggregate import aggregate, check_balance
from whoberi.config import load_config
from whoberi.discover import discover, read_csv
from whoberi.heal import heal_csv
from whoberi.report_context import ReportContext
from whoberi.report_discovery import build_registry, load_plugins
from whoberi.reports import BUILTIN_REPORTS, make_context
from whoberi.types import Entry
from whoberi.validate import validate_column_names, validate_entries


def run_pipeline(root: Path) -> tuple[list[Entry], dict[str, Decimal], AccountRegistry]:
    config = load_config(root)
    registry = load_registry(config)
    ledgers_root = root / config["dirs"]["ledgers"]
    ledgers = discover(ledgers_root)
    entries = []
    for csv_path, handler, meta in ledgers:
        for msg in heal_csv(csv_path):
            print(msg, file=sys.stderr)
        rows = read_csv(csv_path)
        if rows:
            bad_cols = validate_column_names(list(rows[0].keys()))
            if bad_cols:
                raise ValueError(f"{csv_path}: invalid column names: {bad_cols}")
        ledger_key = str(csv_path.relative_to(ledgers_root).with_suffix(""))
        for entry in handler.process(rows, config, meta):
            entry.meta.setdefault("ledger", ledger_key)
            entries.append(entry)
    combined = aggregate(entries)
    return entries, combined, registry


def cmd_discover(root: Path, _args) -> int:
    config = load_config(root)
    ledgers_root = root / config["dirs"]["ledgers"]
    ledgers = discover(ledgers_root)
    if not ledgers:
        print("No ledgers found.")
        return 0
    print(f"{'CSV':<40} {'Handler':<40}")
    print("─" * 80)
    for csv_path, handler, _meta in ledgers:
        print(f"{str(csv_path.relative_to(root)):<40} {str(Path(handler.__file__).relative_to(root)):<40}")
    return 0


def cmd_validate(root: Path, _args) -> int:
    entries, _, registry = run_pipeline(root)
    errors = validate_entries(entries, registry)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print(f"OK — {len(entries)} entries, all balanced.")
    return 0


def cmd_accounts(root: Path, _args) -> int:
    _, combined, _ = run_pipeline(root)
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
    _, combined, registry = run_pipeline(root)
    ctx = ReportContext(entries=[], combined=combined, registry=registry, period=None)
    for t in AccountType:
        total = ctx.sum_type(t)
        print(f"  {t.value.capitalize():<14}  {ctx.fmt(total)}")
    off = check_balance(combined)
    print(f"\n  Balance:          {ctx.fmt(off)}")
    return 0


def cmd_report(root: Path, args) -> int:
    entries, _, registry = run_pipeline(root)
    period = getattr(args, "period", None)
    report_type = args.type

    try:
        custom = load_plugins(root / load_config(root)["dirs"]["reports"])
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    try:
        all_reports = build_registry(BUILTIN_REPORTS, custom)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if report_type == "list":
        width = max(len(n) for n in all_reports)
        print(f"  {'Name':<{width}}  Description")
        print("─" * 60)
        for name in sorted(all_reports):
            rd = all_reports[name]
            src = "" if rd.source == "built-in" else f"  [{Path(rd.source).name}]"
            print(f"  {name:<{width}}  {rd.description}{src}")
        return 0

    try:
        ctx = make_context(entries, registry, period)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if report_type == "all":
        for name in sorted(all_reports):
            try:
                print(all_reports[name].fn(ctx))
                print()
            except (ValueError, KeyError) as e:
                print(f"ERROR in report '{name}': {e}", file=sys.stderr)
                return 1
        return 0

    if report_type not in all_reports:
        available = ", ".join(sorted(all_reports))
        print(f"Unknown report '{report_type}' — available: {available}", file=sys.stderr)
        return 1

    try:
        print(all_reports[report_type].fn(ctx))
    except (ValueError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_add(root: Path, args) -> int:
    config = load_config(root)
    ledgers_root = root / config["dirs"]["ledgers"]
    ledger_path = ledgers_root / (args.ledger + ".csv")
    if not ledger_path.exists():
        print(f"Ledger not found: {ledger_path}", file=sys.stderr)
        return 1
    with open(ledger_path, newline="") as f:
        headers = next(csv_module.reader(f), None)
    if headers is None:
        print(f"Ledger has no header row: {ledger_path}", file=sys.stderr)
        return 1
    if len(args.fields) != len(headers):
        print(
            f"Expected {len(headers)} fields ({', '.join(headers)}), got {len(args.fields)}",
            file=sys.stderr,
        )
        return 1
    with open(ledger_path, "a", newline="") as f:
        writer = csv_module.writer(f)
        writer.writerow(args.fields)
    print(f"Added row to {ledger_path.relative_to(ledgers_root)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whoberi",
        description="Plugin-based accounting CLI",
    )
    parser.add_argument(
        "--root", type=Path, default=Path("."),
        help="Directory containing config.toml (default: current directory)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("discover", help="List detected CSVs and resolved handlers")
    sub.add_parser("validate", help="Run all validation checks")
    sub.add_parser("accounts", help="Print combined account balances")
    sub.add_parser("status", help="Quick summary of balances by account type")

    report_p = sub.add_parser("report", help="Generate financial reports")
    report_p.add_argument("type", help="Report name, 'list', or 'all'")
    report_p.add_argument("--period", help="Period: Q1 2026, 2026-01, 2026")

    add_p = sub.add_parser("add", help="Append a row to a ledger CSV")
    add_p.add_argument("ledger", help="Ledger path relative to the ledgers directory (without .csv)")
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
