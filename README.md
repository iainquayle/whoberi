# whoberi

Plugin-based double-entry accounting CLI for a one-person Canadian software corp. Stdlib only, Python 3.11+.

## Install

```
pip install -e .
```

Exposes the `whoberi` console script.

## Books directory layout

```
<root>/
  config.toml
  income/      *.csv  *.py          # each csv has a same-stem handler
  expenses/    *.csv  *.py
    recurring/ *.csv  *.py
    travel/    *.csv  *.py
  payroll/     *.csv  *.py
  draws/       *.csv  *.py
  imports/     # skipped by discovery
  reports/     # skipped by discovery
```

- Every `*.csv` under `<root>` is a ledger (except under `imports/` or `reports/`).
- Each ledger requires a same-stem handler: `foo.csv` ↔ `foo.py` in the same directory. Missing or unpaired files raise an error.
- CSV stem becomes the account namespace: `income/fooco.csv` → `income:fooco`.

## CLI

```
whoberi [--root <dir>] <cmd>   # default root = .
```

| command | effect |
|---|---|
| `discover` | list ledgers, resolved handler paths, per-ledger overrides |
| `validate` | run pipeline; check zero-sum / account-registry / duplicates; non-zero exit on error |
| `accounts` | print aggregated balances + global zero-sum |
| `status` | cash balance (`assets:venn-cad`) + GST/HST owing |
| `report {pnl\|gst\|payroll\|balance\|annual} [--period Q1\|"Q1 2026"\|2026-01\|2026]` | formatted reports |
| `add <ledger> <fields...>` | append a row to `<root>/<ledger>.csv` |

## Handler contract

```python
from collections.abc import Iterator
from whoberi.types import Entry, LedgerMeta
from decimal import Decimal

def process(rows: list[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]: ...
```

- `Entry(date, accounts: dict[str, Decimal])` — `accounts` must sum to zero (double-entry invariant).
- Account names: colon-separated, hyphen-segmented — e.g. `assets:venn-cad`, `tax:hst-collected`.
- Sign: `+` debit, `−` credit.
- Reference implementations: `tests/fixtures/`.

## config.toml

```toml
[tax]
hst_rate = 0.13

[payroll]
salary = 5000.00
income_tax = 1000.00
cpp = 300.00
ei = 150.00

[accounts]
names = ["assets:venn-cad", "income", "expenses", ...]   # bare name = prefix match

as_of = "2026-01-01"                                     # optional; pins "today" for recurring
import_rules = {"ACME CORP" = "income/acme"}             # used by importer.py (library only)
```

## Caveats

- Pipeline commands **rewrite CSVs in place**: dedup by row hash and sort by `date`. Commit your books before running on real data.
- Handlers are user-supplied — none ship with the package.

## More

- Reference layout and handlers: `tests/fixtures/`
- Run tests: `pytest`
