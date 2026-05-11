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
  books/           # [dirs].ledgers — every *.csv here is a ledger
    income/    *.csv  *.py          # each csv has a same-stem handler
    expenses/  *.csv  *.py
      recurring/ *.csv  *.py
      travel/    *.csv  *.py
    payroll/   *.csv  *.py
    draws/     *.csv  *.py
  imports/         # [dirs].imports — raw bank CSVs
  reports/         # [dirs].reports — report plugin *.py files
```

- Every `*.csv` under the ledgers directory is a ledger.
- Each ledger requires a same-stem handler: `foo.csv` ↔ `foo.py` in the same directory. Missing or unpaired files raise an error.
- CSV stem becomes the account namespace: `income/fooco.csv` → `income:fooco`.
- Directory names are configured in `config.toml` under `[dirs]` — see below.

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
- Account names: bare hyphen-segmented strings — e.g. `venn-cad`, `hst-collected`. No colon prefix. Type comes from the `[accounts]` registry in `config.toml`.
- Every account name emitted must appear in `[accounts]`. Unknown names raise `unknown account '<name>'` at validate time. There are no wildcards or defaults — every account must be enumerated.
- Sign: `+` debit, `−` credit.
- Reference implementations: `tests/fixtures/`.

## config.toml

Top-level keys are system-reserved: `accounts`, `as_of`, `consts`, `dirs`. Any other top-level key is an error.
`[dirs]` is required and names the three per-concern subdirectories (relative to `<root>`).
Put your own numeric constants under `[consts]` and access them in handlers via `config["consts"][...]`.

```toml
[dirs]
ledgers = "books"
imports = "imports"
reports = "reports"

[accounts]
asset     = ["venn-cad"]
liability = ["cra-tax", "cra-cpp", "cra-ei"]
equity    = ["draws", "retained-earnings"]
income    = ["fooco", "barco"]
expense   = ["salary", "software", "recurring"]

as_of = "2026-01-01"                                     # optional; pins "today" for recurring

[consts.tax]
hst_rate = 0.13

[consts.payroll]
salary = 5000.00
income_tax = 1000.00
cpp = 300.00
ei = 150.00
```

## Caveats

- Pipeline commands **rewrite CSVs in place**: dedup by row hash and sort by `date`. Commit your books before running on real data.
- Handlers are user-supplied — none ship with the package.

## More

- Reference layout and handlers: `tests/fixtures/`
- Run tests: `pytest`
