# Workflow

- Run tests: `pytest` from the repo root.
  - The checked-in `.venv` is built for python3.13 while system python is 3.14 —
    `.venv/bin/pytest` fails with `ModuleNotFoundError: No module named 'pytest'`.
    Workaround until the venv is rebuilt:
    `PYTHONPATH=$PWD/.venv/lib/python3.13/site-packages:$PWD python -m pytest -q`
- Manual end-to-end against the reference books:
  `python -m whoberi.main --root examples <validate|report all|document all>`
  `examples/documents/` is generated output and is gitignored.
- Test style: parametrized tables, fixtures in `tests/conftest.py`, `examples/` as the
  integration fixture. Prefer one parametrized test over several near-duplicates.
- Any config-writing test must use `VALID_DIRS` from `conftest`, so a new `[dirs]` key
  is a one-line change.
