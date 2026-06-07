# whoberi

Plain-CSV double-entry bookkeeping driven by Python handler plugins. Your ledger logic
lives in your repo, not inside the tool. Stdlib only, Python 3.11+.

> *Perfectly balanced, as all things should be.* - Thanos

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
    return map(_row_to_entry, rows)

def _row_to_entry(row):
    amount = Decimal(row["amount"])
    return Entry(
        date=date.fromisoformat(row["date"]),
        accounts={"cash": amount, "sales": amount},
    )
```

Both amounts are positive: `cash` is an asset (added to the balance), `sales` is income
(subtracted). Type rule gives `+1000 − 1000 = 0`. See *Accounting model* below.

```
whoberi validate           # OK — 1 entry, all balanced.
whoberi report accounts    # Trial Balance: cash $1,000.00, sales $1,000.00
```

See `examples/` for richer handlers (HST split, payroll from config, `meta.name` to derive
the income account from the CSV stem) and custom reporters.

## Accounting model

whoberi is a single-currency double-entry system. The five standard account types —
`asset`, `liability`, `equity`, `income`, `expense` — are declared in `config.toml`;
together they form your **chart of accounts**. Every account name your handlers emit
must appear there.

Each `Entry` is a journal entry: a date plus one or more `(account, amount)` lines.
Internally the amounts are stored as signed magnitudes (one column) rather than as
separate debit and credit columns — the type of each account fixes its sign in the
balance check (asset and expense add; liability, equity, and income subtract). This is
mathematically identical to classical double-entry: the per-entry signed sum is zero
exactly when total debits equal total credits.

The CLI produces three accountant-facing reports:

- `report pnl` — **Income Statement** (revenue, expenses, net income).
- `report balance` — **Balance Sheet** (assets, liabilities, equity; current-period
  earnings are folded into equity as a synthetic row, so Total assets = Total
  liabilities & equity).
- `report accounts` — **Trial Balance** (all accounts grouped by type, with balances).

Reports display negative amounts in accountant style — `$(493.36)` rather than `$-493.36`.

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
  imports/         # [dirs].imports (reserved; may be absent)
  reports/         # [dirs].reports (custom reporter plugins)
```

`[dirs].imports` is reserved for the bank-CSV importer module; it has no CLI command
yet, and the directory does not need to exist.

- Every `*.csv` under the ledgers directory is a ledger.
- Each ledger requires a same-stem handler: `foo.csv` ↔ `foo.py` in the same directory.
  Missing or unpaired files raise an error.
- CSV stem becomes the account namespace: `income/fooco.csv` → `income:fooco`.
- Directory names are configured in `config.toml` under `[dirs]` (see below).

## CLI

```
whoberi [--root <dir>] <cmd>   # default root = .
```

| command | effect |
|---|---|
| `discover` | list ledgers and resolved handler paths |
| `validate` | run pipeline; check zero-sum / accounts / duplicates; exits non-zero on error |
| `heal` | sort and deduplicate ledger CSVs in place |
| `accounts` | print aggregated balances + global zero-sum |
| `status` | print balances by account type + zero-sum check |
| `report <name>` | run a report; built-ins: `accounts`, `balance`, `pnl`; see `report list` |
| `add <ledger> <fields...>` | append a row to `<ledger>.csv` in the ledgers directory |

`report` accepts `<name>`, `list`, or `all`, plus an optional `--period` filter
(`"Q1 2026"`, `2026-01`, or `2026`).

## Handler contract

```python
from collections.abc import Iterator
from whoberi.types import Entry, LedgerMeta
from decimal import Decimal

def process(rows: list[dict], config: dict, meta: LedgerMeta) -> Iterator[Entry]: ...
```

- `Entry(date, accounts: dict[str, Decimal])`: each `(account, amount)` pair is one
  line of the journal entry. In practice, write positive numbers for accounts that
  increase and negative numbers for accounts that decrease — the signed-magnitude
  convention is detailed in *Accounting model* above.
- Account names: bare hyphen-segmented strings (e.g. `venn-cad`, `hst-collected`).
  Every name must appear in the `[accounts]` chart of accounts; unknown names raise
  `unknown account '<name>'` at validate time. There are no wildcards or defaults.
- Balance rule: the signed sum per entry (asset/expense add; liability/equity/income
  subtract) must be zero. Examples — a $1,000 cash sale: `cash +1000` (asset, added)
  and `sales +1000` (income, subtracted) → 0. Software paid in cash: `software +100`
  (expense, added) and `cash −100` (asset went down, added) → 0.
- Reference implementations: `examples/`.

## config.toml

Top-level keys are system-reserved: `accounts`, `as_of`, `consts`, `dirs`. Any other
top-level key is an error.
`[dirs]` is required and names the three per-concern subdirectories (relative to
`<root>`).
`[accounts]` is your **chart of accounts** — every account name your handlers emit
must appear here under exactly one of the five standard types.
Put your own numeric constants under `[consts]` and access them in handlers via
`config["consts"][...]`.

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

# optional; pins "today" for handlers that need a reference date
as_of = "2026-01-01"

[consts.tax]
hst_rate = 0.13

[consts.payroll]
salary = 5000.00
income_tax = 1000.00
cpp = 300.00
ei = 150.00
```

## Git

Store your books in a git repo. `heal` and `add` write to ledger CSVs (`heal`
rewrites in place to dedup and sort by date; `add` appends a row); commit before
running `heal` on real data. All other commands are read-only.

## Custom reporters

Drop a `*.py` file into the reports directory. Three module attributes are required:

```python
NAME = "gst"
DESCRIPTION = "GST/HST collected vs. paid"

def report(ctx) -> str:
    collected = ctx.combined.get("hst-collected", 0)
    paid = ctx.combined.get("hst-paid", 0)
    return ctx.render(
        [("Collected", collected), ("Paid (ITC)", paid), None, ("Net", collected - paid)],
        title=f"GST/HST{ctx.period_suffix}",
    )
```

`ctx.combined` is a `dict[str, Decimal]` of account balances (period-filtered if
`--period` was passed); `ctx.render` formats a labelled table. `NAME` cannot be
`list` or `all` (CLI sentinels) and cannot shadow a built-in reporter. Invoke via
`whoberi report gst`.

## Plugin self-tests

Any module-level function in a handler or reporter file whose name starts with
`_test_` runs at plugin load time — every CLI invocation that touches the plugin.
One failed `assert` aborts the run with a `ValueError` naming the plugin and the
test. Tests are optional; plugins without `_test_*` functions behave unchanged.

```python
def process(rows, config, meta):
    ...

def _test_basic_split():
    out = list(process([{"date": "2026-01-15", "amount": "113.00", "description": "x"}],
                       {"consts": {"tax": {"hst_rate": 0.13}}}, _META))
    assert out[0].accounts["hst-paid"] == Decimal("13.00")
```

Tests run in sorted order by name. Helpers and constants in the same file are
unaffected — only the `_test_` prefix triggers execution.

## More

- Reference layout and handlers: `examples/`
- Run tests: `pytest`
