# Current state

Last significant work: **document generator plugin system** (plan: `docs/document-plugins-plan.md`).
All four planned phases are implemented; 242 tests pass.

- `whoberi/period.py` and `whoberi/money.py` extracted out of `reporting/` so documents
  can use them without importing the reporting package.
- `whoberi/plugins.py` generalises reporter discovery; `reporter_discovery.py` and
  `documents/document_discovery.py` are now thin `PluginSpec` wrappers.
- `whoberi/documents/` — `Document`/`Payload`, `DocumentContext`, generator discovery, sink.
- `whoberi document <name|list|all> [--period P] [--out DIR] [--force] [--dry-run]`.
- `[dirs]` gained required `generators` and `documents` keys — **breaking** for any
  existing `config.toml`, which must add both.
- `examples/generators/` ships `trial_balance_csv.py` and `invoices_html.py`.

Not done / deliberately deferred: streaming payloads, `document watch`, a generated
manifest, and non-file sinks (email/S3). Reporters were *not* folded into documents.
