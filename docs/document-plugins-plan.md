# Plan — Document generator plugin system

Status: proposal. Nothing implemented.

## Problem

`reporting/` produces `str` for the terminal. That is the wrong shape for artifacts that
leave the machine:

- invoices as PDF
- accountant hand-off as `.xlsx`
- filings / summaries as `.csv`, `.html`, `.json`
- one output *per customer / per month*, not one blob

Reporters cannot express: binary payloads, multiple output files per run, a filename, or
access to individual `Entry` objects (a reporter only sees aggregated balances).

## Goals

- Plugin dir of user-owned document generators, same feel as `reports/`.
- Generators are **pure**: `ctx -> Iterator[Document]`. Core does all disk IO.
- Text and binary payloads, N files per invocation.
- Generators see **individual entries**, not just aggregated balances.
- Core stays **stdlib-only, zero deps**. `reportlab` / `openpyxl` are the *user's*
  dependency, imported inside the user's plugin, never by whoberi (see *Library
  compatibility*).
- Reuse existing machinery — no second copy of plugin loading or period parsing.

## Non-goals

- No built-in document generators shipping PDF/xlsx writers. Core ships a `csv` and an
  `html` example in `examples/`, nothing more.
- No templating engine. A generator is Python; f-strings and the user's own libs suffice.
- No streaming/chunked payloads in v1 (see *Deferred*).

## Core types (ADT)

`whoberi/documents/types.py`

```python
type Payload = str | bytes | bytearray | memoryview   # exhaustively matched at the sink

@dataclass(frozen=True)
class Document:
    name: str                         # relative path incl. extension: "invoices/2026-01-fooco.pdf"
    payload: Payload
```

Sink dispatches on the union, no flags, no encoding guesswork:

```python
match doc.payload:
    case str() as text:
        path.write_text(text, encoding="utf-8")
    case bytes() | bytearray() | memoryview() as blob:
        path.write_bytes(blob)
    case other:
        raise ValueError(
            f"{plugin}: '{doc.name}' payload must be str or bytes-like, "
            f"got {type(other).__name__}"
        )
```

Rationale for a union over `bytes`-only: text generators (`csv`, `html`, `json`) are the
common case and forcing every one of them to `.encode()` is noise.

`bytearray` / `memoryview` are in the union because real libraries return them —
`fpdf2.FPDF.output()` returns a `bytearray`, and `isinstance(bytearray(), bytes)` is
`False`, so a `bytes`-only arm would reject a valid PDF. `Path.write_bytes` accepts any
bytes-like object, so the sink needs no coercion.

## Generator contract

```python
NAME = "invoices"
DESCRIPTION = "One PDF invoice per income entry"

def generate(ctx: DocumentContext) -> Iterable[Document]: ...
```

- Same three-attribute shape as reporters (`NAME` / `DESCRIPTION` / callable), so the
  discovery code is shared (below).
- `_test_*` self-tests work unchanged — they come from `_plugin.load_module`.
- Returning an empty iterable is legal and means "nothing to emit" (reported as such,
  exit 0).

## `DocumentContext`

`whoberi/documents/document_context.py` — strict superset of what a reporter gets.

| field | type | note |
|---|---|---|
| `entries` | `tuple[Entry, ...]` | period-filtered; frozen so a generator cannot mutate shared state |
| `cumulative_entries` | `tuple[Entry, ...]` | date <= period end; mirrors `ReporterContext.cumulative` |
| `combined` | `dict[str, Decimal]` | aggregate of `entries` — same as today's reporters |
| `registry` | `AccountRegistry` | account type lookup |
| `config` | `dict` | static reference data — see *Where data lives* below |
| `period` | `str \| None` | the raw `--period` string |

Deliberately **not** included:

- **An output directory, or any path.** Generators name their files; they never learn
  where the root is. That is what keeps them pure and trivially testable.
- **`Books` / raw source rows.** A generator needing a field the handler dropped is a
  signal that the *handler* should preserve it in `Entry.meta`, not that documents need
  a second read path into the ledgers. Adding it before a real generator demands it
  would be speculative.

Helpers on the context are limited to grouping, since every generator needs it and
nobody should re-derive it:

- `by_ledger() -> dict[str, tuple[Entry, ...]]` — key is the `ledger` meta tag.
- `by_account(name) -> tuple[Entry, ...]`.

The `ledger` tag **already exists** — `run_pipeline` stamps it (`main.py:48`,
`entry.meta.setdefault("ledger", ledger_key)`) with the ledgers-root-relative path,
suffix stripped: `books/income/fooco.csv` -> `"income/fooco"`. `setdefault`, so a
handler that sets its own wins. No core change is needed for any of this.

That tag is `directory/stem`, and both halves are useful:

- **prefix = the group.** `income/` selects every client ledger, so a generator finds
  its inputs without a hardcoded list. Add a client, add a ledger file, the generator
  picks it up.
- **stem = the entity.** It is the `[consts.clients]` key and (by handler convention)
  the account name, so the stem decides which client the document is for and what goes
  on it.

```python
for key, entries in ctx.by_ledger().items():
    directory, _, stem = key.rpartition("/")
    if directory != "income":
        continue
    client = ctx.config["consts"]["clients"][stem]
    ...
```

`fmt_money` moves to a shared spot so documents can use accountant formatting too.

### Where data lives

Documents need more than the ledgers hold — a client address, a company tax number, an
invoice layout. None of that is temporal, so none of it belongs in a ledger file.

| layer | holds | changes |
|---|---|---|
| ledger file (`.csv`/`.tsv`/`.psv`) | temporal facts: what happened, when, for how much | every transaction |
| `[consts]` in `config.toml` | static reference data: company identity, client registry, tax numbers, terms | rarely |
| the generator plugin | presentation: layout, template, logo, fonts | when the document design changes |

The key that joins the first two already exists: **the ledger stem is the entity.**
`books/income/fooco.csv` produces account `fooco` and ledger tag `income/fooco`, so a
generator resolves party details by name:

```toml
[consts.company]
name = "..."
gst  = "..."

[consts.clients.fooco]
name    = "Fooco Industries Ltd."
address = "..."
terms   = "net 30"
```

```python
client = ctx.config["consts"]["clients"][entry.meta["ledger"].split("/")[-1]]
```

A missing client key raises `KeyError` naming it — consistent with how unknown accounts
already fail. No new lookup machinery, no wildcards, no defaults.

Per-transaction facts that genuinely *are* temporal (an invoice number, a PO reference)
belong in the ledger file as a column, and reach documents by the handler copying them
into `Entry.meta`. That path already works today with no core change.

## Refactors first (no behavior change)

Both are prerequisites, both delete duplication rather than adding it.

1. **`whoberi/plugins.py`** — generalise `reporting/reporter_discovery.py`.

   ```python
   @dataclass(frozen=True)
   class PluginSpec:
       kind: str                     # "reporter" | "document"
       entrypoint: str               # "report" | "generate"
       reserved: frozenset[str]      # {"list", "all"}

   @dataclass(frozen=True)
   class PluginDef:
       name: str
       description: str
       fn: Callable
       source: str

   def load_plugins(directory: Path, spec: PluginSpec) -> dict[str, PluginDef]: ...
   def build_registry(builtin, custom, kind) -> dict[str, PluginDef]: ...
   ```

   `reporter_discovery.py` collapses to a `PluginSpec` constant. Every existing error
   (missing attribute, non-str `NAME`, reserved name, duplicate name, built-in conflict)
   is preserved verbatim with `kind` interpolated.

2. **`whoberi/period.py`** — move `_parse_period`, `_PERIOD_PATTERNS`, `_month_end`,
   `filter_by_period`, `filter_as_of`, `period_end_str` out of `reporting/reports.py`.
   Reports imports them from the new home. Documents need the identical filters; the
   parser must not live inside the reporting package.

## New module layout

```
whoberi/
  period.py                        (moved out of reporting/reports.py)
  plugins.py                       (generalised from reporter_discovery.py)
  documents/
    __init__.py
    types.py                       Document, Payload
    document_context.py            DocumentContext + make_document_context()
    document_discovery.py          DOCUMENT_SPEC + load_documents() thin wrapper
    sink.py                        write_documents() — the only IO in the feature
```

`reporting/reporter_discovery.py` keeps its public names, now backed by `plugins.py`.

## Sink — the only IO

`documents/sink.py`

```python
def write_documents(docs: Iterable[Document], out_root: Path, force: bool) -> list[Path]
```

- Resolves `out_root / doc.name`, creates parent dirs, writes by payload type.
- Returns written paths (CLI prints them). Pure-ish orchestrator; all decisions above it.

**Path safety — enumerated, no wildcards:**

| condition | result |
|---|---|
| `name` is empty / whitespace | `ValueError` |
| `name` is absolute (`/x`, `C:\x`) | `ValueError` |
| `name` contains `..` after normalisation | `ValueError` |
| resolved path escapes `out_root` | `ValueError` |
| `name` has no suffix | `ValueError` — extension is how the consumer knows the format |
| target exists, `--force` absent | `ValueError`, nothing written |
| two docs in one run share a `name` | `ValueError`, nothing written |

**Atomicity:** validate the whole batch (names, collisions, existence) *before* writing
any file. A generator that fails halfway must not leave a half-written export dir.

## Config

`[dirs]` gains **two** keys, because plugin source and generated artifacts are different
things and must not share a directory — a `.py` discovery glob over a tree that also
holds emitted files is a bug waiting to happen, and the two have opposite gitignore
needs.

Per the no-defaults rule both are **required**, like the existing three. `load_config`
already rejects unknown and missing keys, so this is a two-line migration for existing
books and a loud error otherwise.

```toml
[dirs]
ledgers    = "books"
imports    = "imports"
reports    = "reports"      # reporter plugins   -> stdout
generators = "generators"   # document plugins   -> files
documents  = "documents"    # OUTPUT: where generated documents land
```

```
<root>/
  generators/
    invoices.py
    year_end_xlsx.py
  documents/                 <- generated; add to .gitignore
    invoices/2026-01-fooco.pdf
    year-end-2026.xlsx
```

`[dirs].documents` is the **default output root**, overridable per invocation with
`--out`. Config names the usual destination; the flag handles the exception (a one-off
export to a client folder or a temp dir).

The `documents/` tree is derived data. README should tell users to gitignore it —
the books repo tracks facts and plugins, not artifacts rebuilt on demand.

## CLI

```
whoberi document <name|list|all> [--period P] [--out DIR] [--force] [--dry-run]
```

| form | effect |
|---|---|
| `document list` | name, description, source file — mirrors `report list` |
| `document all` | run every generator; per-generator failure reported, exit 1, others still run (matches `report all`) |
| `document <name>` | run one; unknown name lists available and exits 1 |
| `--dry-run` | print the paths that *would* be written; no disk writes |
| `--out DIR` | override the output root; default is `<root>/<[dirs].documents>` |
| `--force` | overwrite existing targets |

- Runs `run_pipeline` + `validate_entries` first and refuses to export from books that
  do not validate — same guard `cmd_report` already applies. Exporting an unbalanced
  ledger to a client is the failure mode worth blocking.
- `list` / `all` stay reserved names, enforced by `PluginSpec.reserved`.
- Generator plugins are loaded from `<root>/<[dirs].generators>`.
- Reporter and document namespaces are independent; a `gst` reporter and a `gst`
  generator can coexist. Only collisions *within* a namespace raise.

## Examples (stdlib-only, become fixtures)

`examples/generators/`

- `trial_balance_csv.py` — `NAME = "trial-balance"`, writes one `.csv` via `io.StringIO`
  + `csv.writer`. Proves the text path and the accountant use case.
- `invoices_html.py` — `NAME = "invoices"`, one `.html` per income entry. Selects its
  inputs by ledger prefix (`income/`), resolves client details from `[consts.clients]`
  by ledger stem, names the file from date + stem.
  Proves multi-document output, `by_ledger()`, and the consts lookup.
- Each ships a `_test_*` so the self-test path is exercised on every CLI run.

README gets a **Document generators** section, with a PDF sketch shown but *not* run:

```python
# user's own repo; reportlab is the user's dependency, not whoberi's
from reportlab.pdfgen import canvas

def generate(ctx):
    clients = ctx.config["consts"]["clients"]
    for key, entries in ctx.by_ledger().items():
        directory, _, stem = key.rpartition("/")
        if directory != "income":
            continue
        client = clients[stem]          # KeyError names the missing client
        for entry in entries:
            buf = io.BytesIO()
            ...                          # client["name"], client["address"], entry.date
            yield Document(
                name=f"invoices/{entry.date}-{stem}.pdf",
                payload=buf.getvalue(),
            )
```

That sketch is the whole point of the `bytes` arm and of keeping deps out of core.

## Library compatibility

The `Payload` union is shaped by how PDF/spreadsheet libraries actually hand back data.
Two idioms cover the field, and both end one line before the `yield`:

**Returns bytes directly**

| library | call | type |
|---|---|---|
| WeasyPrint | `HTML(string=html).write_pdf()` | `bytes` |
| reportlab (canvas) | `c.getpdfdata()` | `bytes` |
| pdfkit / wkhtmltopdf | `pdfkit.from_string(html, False)` | `bytes` |
| fpdf2 | `pdf.output()` | `bytearray` |
| pandas | `df.to_csv()` | `str` |

**Writes into a file-like object** — pass `io.BytesIO()`, then `.getvalue()`

| library | call |
|---|---|
| reportlab | `SimpleDocTemplate(buf).build(flowables)` |
| openpyxl | `wb.save(buf)` |
| XlsxWriter | `Workbook(buf, {"in_memory": True})` |
| python-docx | `doc.save(buf)` |
| matplotlib | `fig.savefig(buf, format="png")` |
| stdlib `csv` | `csv.writer(io.StringIO())` |

Notes:

- `BytesIO` is seekable, which is what the PDF and xlsx (zip) writers require. No
  temp files needed for any library in the table.
- Subprocess-backed converters (`pdfkit`/wkhtmltopdf, LibreOffice headless) still need
  their **external binary** installed. That is the user's problem, not whoberi's, but the
  README example should use a pure-Python library so it works out of the box.
- Generators that need to read **input** assets (a logo, a font, an `.html` template)
  can resolve them relative to their own file: `Path(__file__).parent / "logo.png"`.
  Plugin modules are loaded via `spec_from_file_location`, so `__file__` is a real path.
  This is reading, not writing, and does not compromise sink-owns-all-IO.
- `openpyxl.writer.excel.save_virtual_workbook` was removed in openpyxl 3.1 — the
  `BytesIO` form above is the current idiom.

None of these names appear anywhere in whoberi. They are imported inside the user's
plugin file, in the user's books repo, with the user's own `requirements.txt`.

## Tests

Follow existing style — parametrized, fixtures in `conftest.py`, `examples/` as the
integration fixture.

- `test_plugins.py` — shared registry: missing attr, bad `NAME` type, reserved name,
  duplicate, built-in conflict. Parametrized over both `PluginSpec`s so reporters and
  documents are covered by one table.
- `test_period.py` — moved period cases (currently inside `test_reports.py`).
- `test_document_sink.py` — the path-safety table above, one param per row; plus
  "nothing written when any name is invalid".
- `test_documents.py` — `make_document_context` filtering, `by_ledger` / `by_account`.
- `test_cli.py` — add `document list`, `document <name>` writing into `tmp_path`,
  `--dry-run` writes nothing, unknown name exits 1, existing target without `--force`
  exits 1.
- `test_pipeline.py` — extend: run every `examples/generators/` generator, assert the
  expected files appear.

Existing 191 tests must stay green; the refactors are pure moves.

## Phases

1. `period.py` extraction + `plugins.py` generalisation. Tests move, none added. Green.
2. `documents/` types + context + discovery + sink. Unit tests. No CLI yet.
3. `document` CLI command, `[dirs].generators` + `[dirs].documents`, config migration
   for `examples/`.
4. Example generators, README section, pipeline test.

Each phase is independently committable and leaves the suite green.

## Open decisions

1. **`[dirs]` keys.** *Decided:* two required keys — `generators` for document plugins,
   `documents` for output. Both required, consistent with `load_config`'s existing
   strictness; optional would mean a silent default, which the project avoids.
2. **Default `--out`.** *Decided:* `<root>/<[dirs].documents>`, overridable per
   invocation. README gains `.gitignore` guidance for the documents tree.
3. **Should reporters become documents with a stdout sink?** Tempting (one plugin kind,
   two sinks) but recommend *no* for now: reporters return one `str` and are read
   interactively; documents are named files. Sharing `plugins.py` and `period.py`
   captures most of the duplication without forcing a breaking change on every existing
   reporter. Revisit if a third kind appears.
4. **Sink target for non-file outputs** (email, S3, printer). Out of scope; the
   `Document` shape does not preclude adding sinks later.

5. **Client / company reference data.** *Decided:* `[consts]`, keyed by ledger stem, per
   *Where data lives*. Ledger files stay purely temporal; the entity key is the account
   name the project already uses for namespacing. The alternative — constants inside the
   generator plugin — is fine for presentation (layout, logo) but wrong for data, since
   two generators invoicing the same client would each carry their own copy.

6. **Per-recipient documents** (T4 / 1099-style slips). *Follows from 5.* Same mechanism: the recipient is
   a ledger/account, their static details live in `[consts]`, their amounts come from
   entries. No person or entity type is needed in core.

7. **Fillable government PDF forms** need AcroForm field-filling (pypdf, pdftk), which is
   a different library class from PDF *generation*. The `Document` contract is unaffected
   — the plugin still returns bytes — but the README example should not imply that
   generating a PDF and filling a prescribed form are the same task.

## Deferred

- Streaming payloads (`Iterator[bytes]`) for exports too large for memory. The `Payload`
  union is the extension point — add an arm when a real book needs it, not before.
- `document watch` / rebuild-on-change.
- Manifest file listing what was generated when.
