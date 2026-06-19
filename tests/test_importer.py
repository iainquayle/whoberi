import pytest

from whoberi.ledgers.delimited_io import DELIMITERS, read_headers, read_rows, write_rows
from whoberi.ledgers.importer import match_rows, persist_matches

RULES = {
    "AWS": "expenses/software",
    "UBER EATS": "expenses/meals",
    "E-TRANSFER FROM": "income/fooco",
}
FIELDS = ["date", "description", "amount"]


@pytest.fixture
def tmp_root(tmp_path):
    (tmp_path / "expenses").mkdir()
    (tmp_path / "income").mkdir()
    return tmp_path


# --- match_rows (pure) ---

def test_match_returns_target_for_matching_row():
    rows = [{"date": "2026-01-01", "description": "AWS", "amount": "157.50"}]
    pairs = list(match_rows(rows, RULES))
    assert pairs == [(rows[0], "expenses/software")]


def test_match_returns_none_for_unmatched_row():
    rows = [{"date": "2026-01-01", "description": "MYSTERY VENDOR", "amount": "99.00"}]
    pairs = list(match_rows(rows, RULES))
    assert pairs == [(rows[0], None)]


def test_match_case_insensitive():
    rows = [{"date": "2026-01-01", "description": "aws charges", "amount": "50.00"}]
    pairs = list(match_rows(rows, RULES))
    assert pairs[0][1] == "expenses/software"


def test_match_is_lazy():
    """match_rows yields without consuming input upfront."""
    consumed = []
    def gen():
        for row in [{"description": "AWS"}, {"description": "UBER EATS"}]:
            consumed.append(row["description"])
            yield row
    it = match_rows(gen(), RULES)
    assert consumed == []
    next(it)
    assert consumed == ["AWS"]


def test_match_first_rule_wins():
    rules = {"AWS": "a", "AWS BILLING": "b"}
    rows = [{"description": "AWS BILLING charge"}]
    assert list(match_rows(rows, rules))[0][1] == "a"


# --- persist_matches (IO) ---

def test_persist_writes_matched_defaults_csv_in_empty_tree(tmp_root):
    matches = [({"date": "2026-01-01", "description": "AWS", "amount": "157.50"}, "expenses/software")]
    written, skipped = persist_matches(matches, tmp_root)
    assert (written, skipped) == (1, 0)
    target = tmp_root / "expenses" / "software.csv"
    assert target.exists()
    assert list(read_rows(target))[0]["description"] == "AWS"


@pytest.mark.parametrize("dominant_ext", sorted(DELIMITERS))
def test_persist_new_target_adopts_dominant_extension(tmp_root, dominant_ext):
    """New ledgers conform to the format the user already uses in the tree."""
    write_rows(tmp_root / "income" / f"fooco{dominant_ext}", FIELDS, [])
    matches = [({"date": "2026-01-01", "description": "AWS", "amount": "157.50"}, "expenses/software")]
    persist_matches(matches, tmp_root)
    assert (tmp_root / "expenses" / f"software{dominant_ext}").exists()


@pytest.mark.parametrize("suffix", sorted(DELIMITERS))
def test_persist_appends_to_existing_format(tmp_root, suffix):
    """Existing ledgers must be appended in their own format, not coerced to csv."""
    target = tmp_root / "expenses" / f"software{suffix}"
    write_rows(target, FIELDS, [{"date": "2026-01-01", "description": "OLD", "amount": "10.00"}])
    new_row = {"date": "2026-01-02", "description": "AWS", "amount": "157.50"}
    persist_matches([(new_row, "expenses/software")], tmp_root)
    descs = [r["description"] for r in read_rows(target)]
    assert descs == ["OLD", "AWS"]


@pytest.mark.parametrize("suffix", sorted(DELIMITERS))
def test_persist_skips_duplicates(tmp_root, suffix):
    target = tmp_root / "expenses" / f"software{suffix}"
    write_rows(target, FIELDS, [])
    row = {"date": "2026-01-01", "description": "AWS", "amount": "157.50"}
    persist_matches([(row, "expenses/software")], tmp_root)
    written, skipped = persist_matches([(row, "expenses/software")], tmp_root)
    assert (written, skipped) == (0, 1)
    assert len(list(read_rows(target))) == 1


@pytest.mark.parametrize("suffix", sorted(DELIMITERS))
def test_persist_uses_existing_header_order(tmp_root, suffix):
    """Appending must respect the target's existing column order, not the row dict's."""
    target = tmp_root / "expenses" / f"software{suffix}"
    write_rows(target, ["date", "amount", "description"], [
        {"date": "2026-01-01", "amount": "10.00", "description": "OLD"},
    ])
    row = {"description": "NEW", "amount": "20.00", "date": "2026-01-02"}
    persist_matches([(row, "expenses/software")], tmp_root)
    assert read_headers(target) == ["date", "amount", "description"]
    rows = list(read_rows(target))
    assert rows[1] == {"date": "2026-01-02", "amount": "20.00", "description": "NEW"}


@pytest.mark.parametrize("suffix", sorted(DELIMITERS))
def test_persist_rejects_column_mismatch(tmp_root, suffix):
    target = tmp_root / "expenses" / f"software{suffix}"
    write_rows(target, FIELDS, [{"date": "2026-01-01", "description": "OLD", "amount": "10.00"}])
    row = {"date": "2026-01-02", "description": "NEW", "amount": "20.00", "extra": "x"}
    with pytest.raises(ValueError, match="column mismatch"):
        persist_matches([(row, "expenses/software")], tmp_root)


# --- match + persist composition ---

def test_match_and_persist_end_to_end(tmp_root):
    rows = [
        {"date": "2026-01-01", "description": "AWS", "amount": "157.50"},
        {"date": "2026-01-02", "description": "RANDOM CO", "amount": "500.00"},
        {"date": "2026-01-03", "description": "UBER EATS", "amount": "45.00"},
    ]
    pairs = list(match_rows(rows, RULES))
    matched = [(r, t) for r, t in pairs if t is not None]
    unmatched = [r for r, t in pairs if t is None]
    written, skipped = persist_matches(matched, tmp_root)

    assert written == 2
    assert skipped == 0
    assert len(unmatched) == 1
    assert unmatched[0]["description"] == "RANDOM CO"
