# whoberi — project overview

- Plain-text double-entry bookkeeping CLI. Stdlib only, zero runtime deps, Python >= 3.11.
- Books are a git repo of delimited ledger files + Python plugins. whoberi is the engine.
- Signed-magnitude double entry: account *type* fixes the sign
  (`asset`/`expense` = +1, `liability`/`equity`/`income` = -1). An entry balances when the
  type-weighted sum is zero.
- Three plugin kinds, all discovered from disk, all validated loudly at load:
  - **handlers** — same-stem `.py` beside each ledger file; rows -> `Entry`.
  - **reporters** — `[dirs].reports`; `report(ctx) -> str`, printed to stdout.
  - **generators** — `[dirs].generators`; `generate(ctx) -> Iterable[Document]`, written to files.
- Any plugin function named `_test_*` runs at load time on every CLI invocation.
