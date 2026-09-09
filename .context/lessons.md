# Lessons / patterns

- **No wildcards, no defaults.** Unknown account, unknown config key, missing `[dirs]`
  entry, unregistered client: all raise immediately, naming the offender.
- **IO at the edges.** `documents/sink.py` is the only writer in the document feature;
  generators are pure `ctx -> Iterable[Document]` and never learn an output path.
- **Validate the whole batch before writing any of it.** `resolve_targets` checks every
  name, collision, and existing target first; `write_documents` then writes.
- **Reporters and generators share one discovery path** (`plugins.py` + `PluginSpec`).
  Adding a third plugin kind means adding a spec, not a loader.
- **`entry.meta["ledger"]` is `directory/stem`** — prefix selects a group (`income/`),
  stem identifies the entity (the `[consts.clients]` key and the account name). This is
  how generators find inputs by name instead of hardcoding them.
- **Payload is a union, matched exhaustively.** `bytearray` and `memoryview` are separate
  arms because `isinstance(bytearray(), bytes)` is `False` and fpdf2 returns a `bytearray`.
- **Three data layers:** ledger files = temporal facts; `[consts]` = static reference
  data; plugin = presentation. Client addresses never go in a ledger.
