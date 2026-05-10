# Corp Books — Architecture v3

A plugin-based accounting CLI for a single-person Canadian software corporation.

Handlers produce account dicts. The system aggregates and balances.

---

## Design Principles

1. **Enter only what varies.**
2. **Handlers own all derivation.** A handler takes minimal CSV input and produces a dict of named accounts with signed values. No central logic interprets CSV columns.
3. **Handler inheritance.** A `handler.py` applies to all sibling CSVs and all child directories until a deeper `handler.py` is found.
4. **Double-entry as dicts.** Each processed row produces `{"account_name": amount, ...}` where the values sum to zero. Aggregating all dicts across all ledgers gives a full picture of the books, and the zero-sum property is the correctness check.

---

## Directory Layout

```
books/
├── config.toml
├── main.py              # CLI: discovery, aggregation, balance check, reports
├── discover.py          # walks dirs, resolves handlers, pairs with CSVs
├── reports.py           # consumes the combined account dict
├── validate.py          # balance checks, duplicate detection
├── importer.py          # Venn CSV export → sorted into ledger CSVs
│
├── income/
│   ├── handler.py       # handles all CSVs in income/ and below
│   ├── fooco.csv
│   ├── fooco.toml       # optional per-ledger overrides
│   └── barco.csv
│
├── expenses/
│   ├── handler.py       # handles all CSVs in expenses/ and below
│   ├── software.csv
│   ├── office.csv
│   ├── professional_fees.csv
│   └── meals.csv
│
├── payroll/
│   ├── handler.py
│   └── payroll.csv
│
├── draws/
│   ├── handler.py
│   └── draws.csv
│
├── imports/
└── reports/
```

---

## Handler Resolution

When the discovery engine finds a CSV, it walks upward from the CSV's directory until it finds a `handler.py`. That handler processes the CSV.

```
books/
├── handler.py            ← (A) root-level handler, if you wanted one
├── income/
│   ├── handler.py        ← (B) found first for anything in income/
│   ├── fooco.csv         → uses (B)
│   ├── barco.csv         → uses (B)
│   └── recurring/
│       ├── retainer.csv  → uses (B), no handler.py here so inherits from parent
│       └── ...
├── expenses/
│   ├── handler.py        ← (C)
│   ├── software.csv      → uses (C)
│   └── travel/
│       ├── handler.py    ← (D) overrides (C) for this subtree
│       └── flights.csv   → uses (D)
```

Resolution is simple: nearest `handler.py` walking upward from the CSV's directory. No merging, no layering — the closest one wins entirely. In practice the structure will be flat enough that this rarely matters beyond one level.

---

## Handler Interface

Every `handler.py` exposes:

```python
def process(rows: list[dict], config: dict, meta: LedgerMeta) -> list[Entry]
```

### LedgerMeta

Contextual information auto-populated by the discovery engine:

```python
@dataclass
class LedgerMeta:
    name: str               # CSV stem: "fooco", "software", "payroll"
    directory: str           # parent dir name: "income", "expenses", etc.
    path: Path              # full path to the CSV
    overrides: dict         # contents of per-ledger .toml if present
```

### Entry

What a handler returns per row:

```python
@dataclass
class Entry:
    date: date
    description: str
    accounts: dict[str, Decimal]    # the double-entry output
    meta: dict                      # optional: notes, invoice numbers, whatever
```

The `accounts` dict is the heart of it. Keys are account names, values are signed amounts. **Every Entry's accounts must sum to zero.**

---

## The Accounts Dict

This is how double-entry works without the ceremony. A handler takes in minimal input and maps it to named accounts with signs that reflect the flow of money.

### Example: Expense (software subscription, $157.50 HST-inclusive in Ontario)

CSV row input:

```
2026-05-01, AWS, 157.50
```

Handler output:

```python
Entry(
    date=date(2026, 5, 1),
    description="AWS",
    accounts={
        "expenses:software":     Decimal("139.38"),    # pre-tax cost
        "tax:hst_paid":          Decimal("18.12"),     # input tax credit
        "assets:venn_cad":       Decimal("-157.50"),   # money left the account
    }
)
# sum: 139.38 + 18.12 + (-157.50) = 0.00 ✓
```

### Example: Income (client payment, $5,250 HST-inclusive)

CSV row input:

```
2026-05-01, Invoice 42, 5250.00
```

Handler output:

```python
Entry(
    date=date(2026, 5, 1),
    description="Invoice 42",
    accounts={
        "assets:venn_cad":       Decimal("5250.00"),   # money came in
        "income:fooco":          Decimal("-4646.02"),   # revenue (negative = credit)
        "tax:hst_collected":     Decimal("-603.98"),    # HST liability
    }
)
# sum: 5250.00 + (-4646.02) + (-603.98) = 0.00 ✓
```

### Example: Payroll (date-only input)

CSV row input:

```
2026-05-15
```

Handler output:

```python
Entry(
    date=date(2026, 5, 15),
    description="Payroll 2026-05-15",
    accounts={
        "expenses:salary":           Decimal("5000.00"),
        "liabilities:cra_tax":       Decimal("-1000.00"),
        "liabilities:cra_cpp":       Decimal("-300.00"),
        "liabilities:cra_ei":        Decimal("-150.00"),
        "assets:venn_cad":           Decimal("-3550.00"),
    }
)
# sum: 5000.00 + (-1000.00) + (-300.00) + (-150.00) + (-3550.00) = 0.00 ✓
```

### Example: Shareholder draw

CSV row input:

```
2026-05-20, 3000.00
```

Handler output:

```python
Entry(
    date=date(2026, 5, 20),
    description="Shareholder draw",
    accounts={
        "equity:draws":          Decimal("3000.00"),
        "assets:venn_cad":       Decimal("-3000.00"),
    }
)
# sum: 0.00 ✓
```

---

## Account Naming Convention

Account names are freeform strings, but consistency matters because the aggregation and reports depend on them lining up across handlers.

Recommended convention — colon-separated hierarchy:

```
assets:venn_cad
assets:venn_usd
income:fooco
income:barco
expenses:software
expenses:office
expenses:meals
expenses:salary
tax:hst_collected
tax:hst_paid
liabilities:cra_tax
liabilities:cra_cpp
liabilities:cra_ei
equity:draws
equity:retained_earnings
```

### Keeping names consistent

The risk is one handler calling it `tax:hst_paid` and another calling it `tax:gst_paid` or `tax:hst-paid`. Two mitigation strategies, pick one:

**Option A — Account registry in config.toml:**

```toml
[accounts]
names = [
    "assets:venn_cad",
    "assets:venn_usd",
    "income",               # prefix: any "income:*" is valid
    "expenses",             # prefix: any "expenses:*" is valid
    "tax:hst_collected",
    "tax:hst_paid",
    "liabilities:cra_tax",
    "liabilities:cra_cpp",
    "liabilities:cra_ei",
    "equity:draws",
    "equity:retained_earnings",
]
```

The validator checks every account name in every Entry against this list. Unknown names → warning. This catches typos without being rigid.

**Option B — Shared constants module:**

```python
# accounts.py
VENN_CAD = "assets:venn_cad"
HST_COLLECTED = "tax:hst_collected"
HST_PAID = "tax:hst_paid"
# ...
```

Handlers import and use these. Typos become import errors.

Option B is more Pythonic and catches mistakes earlier. Option A is more accessible if you want non-developers to understand the system. Either works.

---

## Aggregation

After discovery runs all handlers, the system has a flat `list[Entry]`. Aggregation is straightforward:

```python
combined = defaultdict(Decimal)
for entry in all_entries:
    for account, amount in entry.accounts.items():
        combined[account] += amount
```

The result is one dict with every account and its running total. This is your entire financial state.

### The Balance Check

```python
total = sum(combined.values())
assert total == Decimal("0.00"), f"Books don't balance: off by {total}"
```

If this fails, something is wrong in a handler or a CSV. The system can report which entries are unbalanced individually to narrow it down.

---

## Per-Ledger Config Overrides

Optional `.toml` file matching the CSV name, passed to the handler via `meta.overrides`.

`income/barco.toml`:
```toml
currency = "USD"
tax_applies = false     # foreign client, no HST
```

`expenses/meals.toml`:
```toml
deduction_rate = 0.50   # CRA 50% meals deduction
```

The handler reads these and adjusts its output accordingly. The system doesn't interpret them — they're opaque to everything except the handler that receives them.

---

## Reports (reports.py)

All reports are views over the combined accounts dict, optionally filtered by date range.

### P&L

```
Sum all "income:*" accounts → Revenue
Sum all "expenses:*" accounts → Expenses
  Apply deduction rates where configured (meals at 50%)
Revenue - Expenses = Net income
```

### GST/HST Return

```
tax:hst_collected  → total collected
tax:hst_paid       → total input tax credits
Net = collected - paid (both are absolute values; signs handled in display)
```

### Payroll Summary

```
expenses:salary              → gross paid
liabilities:cra_tax          → withheld income tax (if negative balance, unremitted)
liabilities:cra_cpp          → withheld CPP
liabilities:cra_ei           → withheld EI
```

When you remit to CRA, you'd record an entry that debits the liability and credits the bank, zeroing them out.

### Balance Sheet

```
Assets:   sum all "assets:*"
Liabilities: sum all "liabilities:*"
Equity:   sum all "equity:*"
Assets = Liabilities + Equity  (verified by the zero-sum property)
```

### Year-End Package

All of the above for the fiscal year, exported to `reports/` as markdown or CSV for accountant handoff.

---

## Bank Import (importer.py)

```
1. Read Venn CSV export from imports/
2. Match each row against import rules (vendor patterns → target CSV)
3. Append matched rows to target CSVs in the minimal schema that handler expects
4. Print unmatched rows for manual review
5. Optionally prompt to add new rules for unmatched vendors
```

```toml
[import_rules]
"AWS"              = "expenses/software"
"GITHUB"           = "expenses/software"
"UBER EATS"        = "expenses/meals"
"E-TRANSFER FROM"  = "income"
```

Importer only appends. Duplicate detection happens in validation.

---

## Validation (validate.py)

### Per-Entry

- `accounts` sums to zero
- Date is parseable and within fiscal year
- All account names are recognized (if using registry)

### Cross-Entry

- Duplicate detection: same date + description + amount within a ledger
- Payroll YTD: CPP/EI haven't exceeded annual caps
- Missing periods: expected recurring entries that aren't present

### Reconciliation

- `assets:venn_cad` running total vs. actual bank balance (manually provided or from latest import)
- If they diverge → something is missing or miscategorized

---

## CLI

```
books discover                        # list detected CSVs, resolved handlers, account names
books add <ledger> [fields...]        # append a row
books import <file>                   # process Venn export
books validate                        # run all checks
books status                          # quick: cash, GST owing, next payroll due
books accounts                        # print combined accounts dict, current balances
books report pnl [--period Q1]
books report gst [--period Q1]
books report payroll [--year 2026]
books report balance
books report annual
```

---

## Recurring Transactions

Recurring transactions are regular CSVs with a handler that expands date ranges. The CSV schema adds three columns to whatever the handler requires:

| Column | Description |
|---|---|
| `date` | First occurrence |
| `end_date` | Last occurrence (empty = ongoing, capped at today) |
| `period` | `monthly`, `semi-monthly`, or `weekly` |

The handler uses `whoberi.dateutil.expand_dates` to generate one entry per occurrence from `date` through `min(end_date, as_of)`. Placing the CSV in a subdirectory with its own `handler.py` overrides the parent handler, keeping recurring logic co-located with the ledger it belongs to.

To test with a fixed date, set `as_of` in the config dict passed to the handler.

---

## What This Doesn't Do

- File taxes — gives numbers, you file on CRA My Business Account
- Generate invoices — Venn or a template
- Replace an accountant — produces clean inputs for one
- Multi-entity or multi-user

---

## Extension Points

- New client → create a CSV in `income/`
- New expense category → create a CSV in `expenses/`
- Fundamentally different transaction type → new directory with a `handler.py`
- New bank account → add an account name, update relevant handlers to use it
- Province change → update config.toml tax rates
- Second employee → payroll handler reads a list from config

The architecture changes only if the Entry contract changes.
