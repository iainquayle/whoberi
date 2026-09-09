# Layout

```
whoberi/
  main.py                 CLI + run_pipeline (stamps entry.meta["ledger"] = "dir/stem")
  config.py               config.toml load + strict [dirs]/[accounts]/[consts] validation
  accounts.py             AccountType, AccountRegistry (type_of / sign_of)
  aggregate.py            aggregate, check_balance, is_balanced
  validate.py             column names, balance, duplicates
  types.py                Entry, LedgerMeta
  money.py                fmt_money — shared by reporting and documents
  period.py               period parsing + filter_by_period / filter_as_of / period_end_str
  plugins.py              PluginSpec/PluginDef, load_plugins, build_registry (reporters + documents)
  _plugin.py              module loading + _test_* execution
  ledgers/                delimited IO, handler discovery, Books, heal, importer
  reporting/              reporter_context, reporter_discovery, reports (built-ins)
  documents/              types (Document/Payload), document_context, document_discovery, sink
examples/                 reference books: config.toml, books/, reports/, generators/
tests/                    pytest; conftest holds fixtures (FIXTURES, VALID_DIRS, SAMPLE_ENTRIES)
docs/                     design docs (document-plugins-plan.md)
```

`[dirs]` names five required directories: `ledgers`, `imports`, `reports`,
`generators`, `documents`. Missing or unknown keys are an error — no defaults.
