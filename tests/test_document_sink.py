"""Sink path safety and atomicity."""
import pytest

from whoberi.documents.sink import write_documents
from whoberi.documents.types import Document


@pytest.mark.parametrize("name,match", [
    ("", "is empty"),
    ("   ", "is empty"),
    ("/abs.csv", "must be relative"),
    ("C:\\abs.csv", "must be relative"),
    ("../escape.csv", "must not contain"),
    ("a/../../escape.csv", "must not contain"),
    ("noextension", "file extension"),
])
def test_invalid_names_raise(tmp_path, name, match):
    with pytest.raises(ValueError, match=match):
        write_documents([Document(name=name, payload="x")], tmp_path, force=False)


def test_symlinked_subdir_escaping_root_raises(tmp_path):
    out_root = tmp_path / "out"
    out_root.mkdir()
    (tmp_path / "outside").mkdir()
    (out_root / "link").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="escapes the output root"):
        write_documents([Document(name="link/x.csv", payload="x")], out_root, force=False)


@pytest.mark.parametrize("payload,expected", [
    ("text", b"text"),
    (b"bytes", b"bytes"),
    (bytearray(b"bytearray"), b"bytearray"),
    (memoryview(b"memoryview"), b"memoryview"),
])
def test_payload_types_written(tmp_path, payload, expected):
    [path] = write_documents([Document(name="a/b.bin", payload=payload)], tmp_path, force=False)
    assert path.read_bytes() == expected


def test_unsupported_payload_raises(tmp_path):
    with pytest.raises(ValueError, match="must be str or bytes-like, got int"):
        write_documents([Document(name="a.txt", payload=42)], tmp_path, force=False)


def test_duplicate_names_raise(tmp_path):
    docs = [Document(name="a.txt", payload="1"), Document(name="a.txt", payload="2")]
    with pytest.raises(ValueError, match="resolve to"):
        write_documents(docs, tmp_path, force=False)


def test_existing_target_requires_force(tmp_path):
    doc = Document(name="a.txt", payload="1")
    write_documents([doc], tmp_path, force=False)
    with pytest.raises(ValueError, match="already exists"):
        write_documents([doc], tmp_path, force=False)
    write_documents([Document(name="a.txt", payload="2")], tmp_path, force=True)
    assert (tmp_path / "a.txt").read_text() == "2"


def test_batch_validated_before_any_write(tmp_path):
    docs = [Document(name="good.txt", payload="1"), Document(name="../bad.txt", payload="2")]
    with pytest.raises(ValueError):
        write_documents(docs, tmp_path, force=False)
    assert not (tmp_path / "good.txt").exists()
