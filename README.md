# whoberi

Plain-CSV double-entry bookkeeping driven by Python handler plugins. Your ledger logic lives in your repo, not inside the tool. Stdlib only, Python 3.11+.

> *Balanced, as all things should be.* - Thanos

## Install

From a local checkout:

```
pip install -e .
```

Directly from a git repo:

```
pip install git+https://github.com/<owner>/whoberi.git
pip install git+https://github.com/<owner>/whoberi.git@<tag-or-sha>
```

Either form exposes the `whoberi` console script.

## Quick start

```
mkdir mybooks && cd mybooks && git init
```

`config.toml`:

```toml
[dirs]
ledgers = "books"
imports = "imports"
reports = "reports"

[accounts]
asset  = ["cash"]
income = ["sales"]
```

`books/sales.csv`:

```
date,amount
2026-01-15,1000
```

`books/sales.py`:

```python
from datetime import date
from decimal import Decimal
from whoberi.types import Entry

def process(rows, config, meta):
    for r in rows:
        amount = Decimal(r["amount"])
        yield Entry(
            date=date.fromisoformat(r["date"]),
            accounts={"cash": amount, meta.name: -amount},
        )
```

```
whoberi validate           # OK — 1 entries, all balanced.
whoberi report accounts    # cash $1,000.00 / sales $-1,000.00
```

See `examples/` for richer handlers (HST split, payroll from config) and custom reporters.

## Project layout (example)

```
<root>/
  config.toml
  books/           # [dirs].ledgers
    foo.csv
    foo.py         # same-stem handler
    bar/
      baz.csv
      baz.py
  reports/         # [dirs].reports (custom reporter plugins)
```

`[dirs].imports` is also reserved (for a future import command); the directory does not need to exist.

- Every `*.csv` under the ledgers directory is a ledger.
- Each ledger requires a same-stem handler: `foo.csv` ↔ `foo.py` in the same directory. Missing or unpaired files raise an error.
- CSV stem becomes the account namespace: `income/fooco.csv` → `income:fooco`.
- Directory names are configured in `config.toml` under `[dirs]` (see below).

## CLI

```
whoberi [--root <dir>] <cmd>   # default root = .
```

| command | effect |
|---|---|
| `discover` | list ledgers and resolved handler paths |
| `validate` | run pipeline; check zero-sum / account-registry / duplicates; non-zero exit on error |
| `heal` | sort and deduplicate ledger CSVs in place |
| `accounts` | print aggregated balances + global zero-sum |
| `status` | print balances by account type + zero-sum check |
| `report <name\|list\|all> [--period "Q1 2026"\|2026-01\|2026]` | run a report; built-ins: `accounts`, `balance`, `pnl`; use `report list` to see all |
| `add <ledger> <fields...>` | append a row to `<ledger>.csv` in the ledgers directory |

## Handler contract

```python
from collections.abc import Iterator
from whoberi.types import Entry, LedgerMeta
from decimal import Decimal

def process(rows: list[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]: ...
```

- `Entry(date, accounts: dict[str, Decimal])`: `accounts` must sum to zero (double-entry invariant).
- Account names: bare hyphen-segmented strings, e.g. `venn-cad`, `hst-collected`. No colon prefix. Type comes from the `[accounts]` registry in `config.toml`.
- Every account name emitted must appear in `[accounts]`. Unknown names raise `unknown account '<name>'` at validate time. There are no wildcards or defaults; every account must be enumerated.
- Sign: `+` debit, `−` credit.
- Reference implementations: `examples/`.

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

as_of = "2026-01-01"                                     # optional; pins "today" for handlers that need a reference date

[consts.tax]
hst_rate = 0.13

[consts.payroll]
salary = 5000.00
income_tax = 1000.00
cpp = 300.00
ei = 150.00
```

## Git

Store your books in a git repo. `whoberi heal` rewrites CSVs in place (dedup + sort by date); commit before running it on real data. Other commands read but never write.

## Caveats

- Handlers are user-supplied; none ship with the package.

## Custom reporters

Drop a `*.py` file into the reports directory. Three module attributes are required:

```python
NAME = "gst"
DESCRIPTION = "GST/HST collected vs. paid"

def report(ctx) -> str:
    collected = -ctx.combined.get("hst-collected", 0)
    paid = ctx.combined.get("hst-paid", 0)
    return ctx.render(
        [("Collected", collected), ("Paid (ITC)", paid), None, ("Net", collected - paid)],
        title=f"GST/HST{ctx.period_suffix}",
    )
```

`ctx.combined` is a `dict[str, Decimal]` of account balances (period-filtered if `--period` was passed); `ctx.render` formats a labelled table. `NAME` cannot be `list` or `all` (CLI sentinels) and cannot shadow a built-in reporter. Invoke via `whoberi report gst`.

## More

- Reference layout and handlers: `examples/`
- Run tests: `pytest`
