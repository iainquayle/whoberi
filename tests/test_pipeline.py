"""Integration test: discover -> process -> aggregate -> balance = 0."""
from whoberi.aggregate import check_balance, is_balanced
from whoberi.documents.document_context import make_document_context
from whoberi.documents.document_discovery import load_generators
from whoberi.documents.sink import write_documents
from whoberi.main import run_pipeline
from tests.conftest import FIXTURES


def test_pipeline_all_entries_balanced():
    result = run_pipeline(FIXTURES)
    assert len(result.entries) > 0
    assert all(is_balanced(e, result.registry) for e in result.entries)
    assert check_balance(result.combined, result.registry) == 0


def test_example_generators_emit_expected_documents(tmp_path):
    result = run_pipeline(FIXTURES)
    ctx = make_document_context(result.entries, result.registry, result.config, None)
    generators = load_generators(FIXTURES / "generators")
    written = [
        path.relative_to(tmp_path)
        for name in sorted(generators)
        for path in write_documents(generators[name].fn(ctx), tmp_path, force=False)
    ]
    assert {str(p) for p in written} == {
        "invoices/2026-01-15-fooco.html",
        "invoices/2026-02-01-barco.html",
        "trial-balance.csv",
    }
