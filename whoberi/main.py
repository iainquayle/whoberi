import argparse
import csv
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from whoberi.accounts import AccountRegistry, AccountType, load_registry
from whoberi.aggregate import aggregate, check_balance
from whoberi.config import load_config
from whoberi.ledgers.csv_io import read_csv, read_csv_headers
from whoberi.ledgers.handler_discovery import discover
from whoberi.ledgers.heal import heal_file
from whoberi.reporting.reporter_context import ReporterContext, fmt_money
from whoberi.reporting.reporter_discovery import build_reporter_registry, load_reporters
from whoberi.reporting.reports import BUILTIN_REPORTERS, make_context
from whoberi.types import Entry
from whoberi.validate import validate_column_names, validate_entries


@dataclass(frozen=True)
class PipelineResult:
    entries: list[Entry]
    combined: dict[str, Decimal]
    registry: AccountRegistry
    config: dict


def run_pipeline(root: Path) -> PipelineResult:
    config = load_config(root)
    registry = load_registry(config)
    ledgers_root = root / config["dirs"]["ledgers"]
    ledgers = discover(ledgers_root)
    entries: list[Entry] = []
    for csv_path, handler, meta in ledgers:
        rows = list(read_csv(csv_path))
        if rows:
            bad_cols = validate_column_names(rows[0].keys())
            if bad_cols:
                raise ValueError(f"{csv_path}: invalid column names: {bad_cols}")
        ledger_key = str(csv_path.relative_to(ledgers_root).with_suffix(""))
        for entry in handler.process(rows, config, meta):
            entry.meta.setdefault("ledger", ledger_key)
            entries.append(entry)
    return PipelineResult(
        entries=entries,
        combined=aggregate(entries),
        registry=registry,
        config=config,
    )


def heal_ledgers(root: Path) -> list[str]:
    config = load_config(root)
    ledgers_root = root / config["dirs"]["ledgers"]
    logs: list[str] = []
    for csv_path, _, _ in discover(ledgers_root):
        logs.extend(heal_file(csv_path))
    return logs


def _fail_with_errors(errors: list[str]) -> int:
    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    return 1


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
    result = run_pipeline(root)
    errors = validate_entries(result.entries, result.registry)
    if errors:
        return _fail_with_errors(errors)
    n = len(result.entries)
    print(f"OK — {n} {'entry' if n == 1 else 'entries'}, all balanced.")
    return 0


def cmd_heal(root: Path, _args) -> int:
    logs = heal_ledgers(root)
    for msg in logs:
        print(msg)
    if not logs:
        print("No changes.")
    return 0


def cmd_accounts(root: Path, _args) -> int:
    result = run_pipeline(root)
    if not result.combined:
        print("No accounts.")
        return 0
    width = max(len(k) for k in result.combined)
    for account in sorted(result.combined):
        print(f"  {account:<{width}}  {fmt_money(result.combined[account]):>14}")
    off = check_balance(result.combined, result.registry)
    print(f"\n  {'Balance check':<{width}}  {fmt_money(off):>14}")
    return 0


def cmd_status(root: Path, _args) -> int:
    result = run_pipeline(root)
    ctx = ReporterContext(
        combined=result.combined, cumulative=result.combined, registry=result.registry, period=None
    )
    for t in AccountType:
        total = ctx.sum_type(t)
        print(f"  {t.value.capitalize():<14}  {ctx.fmt(total)}")
    off = check_balance(result.combined, result.registry)
    print(f"\n  Balance:          {ctx.fmt(off)}")
    return 0


def cmd_report(root: Path, args) -> int:
    report_type = args.type
    config = load_config(root)
    custom = load_reporters(root / config["dirs"]["reports"])
    all_reports = build_reporter_registry(BUILTIN_REPORTERS, custom)

    if report_type == "list":
        width = max(len(n) for n in all_reports)
        print(f"  {'Name':<{width}}  Description")
        print("─" * 60)
        for name in sorted(all_reports):
            rd = all_reports[name]
            src = "" if rd.source == "built-in" else f"  [{Path(rd.source).name}]"
            print(f"  {name:<{width}}  {rd.description}{src}")
        return 0

    result = run_pipeline(root)
    validation_errors = validate_entries(result.entries, result.registry)
    if validation_errors:
        return _fail_with_errors(validation_errors)

    ctx = make_context(result.entries, result.registry, args.period)

    if report_type == "all":
        failed: list[str] = []
        for name in sorted(all_reports):
            try:
                print(all_reports[name].fn(ctx))
                print()
            except (ValueError, KeyError) as e:
                print(f"ERROR in report '{name}': {e}", file=sys.stderr)
                failed.append(name)
        return 1 if failed else 0

    if report_type not in all_reports:
        available = ", ".join(sorted(all_reports))
        print(f"Unknown report '{report_type}' — available: {available}", file=sys.stderr)
        return 1

    print(all_reports[report_type].fn(ctx))
    return 0


def cmd_add(root: Path, args) -> int:
    config = load_config(root)
    ledgers_root = root / config["dirs"]["ledgers"]
    ledger_path = ledgers_root / (args.ledger + ".csv")
    if not ledger_path.exists():
        print(f"Ledger not found: {ledger_path}", file=sys.stderr)
        return 1
    headers = read_csv_headers(ledger_path)
    if not headers:
        print(f"Ledger has no header row: {ledger_path}", file=sys.stderr)
        return 1
    if len(args.fields) != len(headers):
        print(
            f"Expected {len(headers)} fields ({', '.join(headers)}), got {len(args.fields)}",
            file=sys.stderr,
        )
        return 1
    with open(ledger_path, "a", newline="") as f:
        writer = csv.writer(f)
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
    sub.add_parser("heal", help="Sort and deduplicate ledger CSVs in place")
    sub.add_parser("accounts", help="Print combined account balances")
    sub.add_parser("status", help="Print balances by account type with overall balance check")

    report_p = sub.add_parser("report", help="Generate financial reports")
    report_p.add_argument("type", help="Report name, 'list', or 'all'")
    report_p.add_argument("--period", help="Period: \"Q1 2026\", 2026-01, 2026")

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
        "heal": cmd_heal,
        "accounts": cmd_accounts,
        "status": cmd_status,
        "report": cmd_report,
        "add": cmd_add,
    }

    try:
        sys.exit(commands[args.command](root, args))
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
