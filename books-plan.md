# Plan: `books` accessor for handlers

Give a handler read access to *another ledger's source rows* via an injected
`books` accessor. Lazy and streaming — the accessor holds paths only, never
contents, so absolute memory overhead stays flat regardless of book size.

## Decisions

- **Interface only.** Scope is the cross-book read mechanism, not any specific
  use case built on top of it.
- **Source rows, not entries.** A handler reads another book's *raw rows* (static
  input), never its computed entries. This is what makes it order-independent —
  no eval ordering, no dependency graph.
- **Lazy + streaming.** `Books` holds `{ledger_key: Path}` only. `rows(name)`
  returns a fresh streaming `Iterator[dict]` per call via `read_rows`. Contents
  are never cached.
  - Multi-pass / random access is the handler's explicit choice: call again to
    re-iterate (re-reads file), or `list(books.rows(name))` to materialize and
    own the memory. Matches the Iterable-default convention.
  - Trade accepted: no cache ⇒ re-read per pass (CPU/IO), in exchange for flat
    absolute memory. IO now fires at handler-call time through the injected edge
    object — a deliberate, named bend of the IO-at-edge rule; all reads still
    funnel through `delimited_io`.
- **Injection: 4th positional param** `process(rows, config, meta, books)`.
  Breaks the handler signature → migrate examples + self-tests. Chosen over
  hanging it on `meta` (keeps `LedgerMeta` single-responsibility).
- **Loud on miss.** Unknown book name raises `KeyError` listing available books.
  `books` only exposes handler-paired ledgers (built from `discover`), so stray
  files never leak in.

## Changes

### 1. New `whoberi/ledgers/books.py`
Edge object — IO lives here, keeps `types.py` pure.
```python
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from whoberi.ledgers.delimited_io import read_rows


@dataclass(frozen=True)
class Books:
    _paths: dict[str, Path]                 # ledger key -> source path; no contents

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._paths))

    def rows(self, name: str) -> Iterator[dict]:
        try:
            path = self._paths[name]
        except KeyError:
            avail = ", ".join(sorted(self._paths)) or "(none)"
            raise KeyError(f"unknown book '{name}' — available: {avail}")
        return read_rows(path)              # fresh streaming reader; never cached
```

### 2. `whoberi/main.py` — `run_pipeline` (lines 29–50)
- Build the path map from `discover` (cheap, no reads), reusing the existing
  `ledger_key` formula (`relative_to(ledgers_root).with_suffix("")`, line 41).
- Construct `Books(paths)` once.
- Pass it as the 4th arg: `handler.process(rows, config, meta, books)` (line 42).
- Handler's own-rows handling (line 36) is unchanged.
- Add `from whoberi.ledgers.books import Books`.

### 3. Example handlers (add `books` param + fix `_test_` calls)
- `examples/books/income/fooco.py`, `barco.py`
- `examples/books/expenses/software.py`, `recurring/recurring.py`
- `examples/books/payroll/payroll.py`
- `examples/books/draws/draws.py`

Each: `def process(rows, config, meta):` → `def process(rows, config, meta, books):`
(param unused where not needed). Every `_test_*` that calls `process(...)` adds a
4th arg — pass `Books({})`, or `Books({"some/book": path})` for a test that
exercises a read.

### 4. Tests
- `tests/test_handlers.py`, `tests/conftest.py` — update any direct `process(...)`
  call to pass `books` (e.g. `Books({})`).
- New `tests/test_books.py` (or add to `test_pipeline.py`):
  - handler reads another book's rows via `books.rows(key)` → gets expected rows.
  - unknown book name raises `KeyError` naming available books.
  - `rows()` yields a fresh iterator each call (re-iterate works; not exhausted).
  - end-to-end: a handler reading a sibling book runs through `run_pipeline`.

### 5. README.md
- Handler contract (lines 149–170): document the 4-arg signature and `books`.
- Quick-start handler (lines 51–67): bump to 4 args.
- New short subsection "Reading another book":
  - `books.rows(stem)` streams another ledger's *source rows* by its
    ledgers-relative stem (e.g. `income/fooco`).
  - It reads source rows, not computed entries — order-independent.
  - Streaming + uncached: re-iterate by calling again; `list(...)` to materialize.
  - Unknown name raises, listing available books.

## Notes / edge cases
- `books.rows` returns raw rows; `read_rows` still runs the wrong-delimiter
  `_check_header` guard. Column-name validation (`validate_column_names`) runs
  when each book is processed in its own loop turn, not on cross-book reads.
- A handler may read its own book (harmless re-read) or a book not yet processed
  (fine — raw source rows are order-independent).
- Generators hold the file open until exhausted/closed; fully consuming (or
  `list(...)`) is the norm.

## Out of scope
- The interval-transfer / date-summing use case (built on top of this, separately).
- `[dirs].data` reference-table directory for non-ledger lookup CSVs.
- Reading another handler's *computed entries* (order-dependent — deliberately
  excluded).
