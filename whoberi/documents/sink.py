"""The only IO in the document feature: validate a whole batch, then write it."""
from collections.abc import Iterable
from pathlib import Path, PurePosixPath, PureWindowsPath

from whoberi.documents.types import Document


def resolve_targets(
    docs: Iterable[Document], out_root: Path, force: bool
) -> list[tuple[Document, Path]]:
    """Validate every name and resolve it under `out_root`. Raises before anything is written."""
    root = out_root.resolve()
    targets: list[tuple[Document, Path]] = []
    claimed: dict[Path, str] = {}
    for doc in docs:
        target = (root / _validate_name(doc.name)).resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"document name escapes the output root: '{doc.name}'")
        if target in claimed:
            raise ValueError(
                f"two documents resolve to {target}: '{claimed[target]}' and '{doc.name}'"
            )
        if target.exists() and not force:
            raise ValueError(f"{target} already exists — pass --force to overwrite")
        claimed[target] = doc.name
        targets.append((doc, target))
    return targets


def write_documents(docs: Iterable[Document], out_root: Path, force: bool) -> list[Path]:
    written: list[Path] = []
    for doc, target in resolve_targets(docs, out_root, force):
        target.parent.mkdir(parents=True, exist_ok=True)
        match doc.payload:
            case str() as text:
                target.write_text(text, encoding="utf-8")
            case bytes() | bytearray() | memoryview() as blob:
                target.write_bytes(blob)
            case other:
                raise ValueError(
                    f"'{doc.name}' payload must be str or bytes-like, "
                    f"got {type(other).__name__}"
                )
        written.append(target)
    return written


def _validate_name(name: str) -> PurePosixPath:
    if not name.strip():
        raise ValueError("document name is empty")
    if PurePosixPath(name).is_absolute() or PureWindowsPath(name).is_absolute():
        raise ValueError(f"document name must be relative: '{name}'")
    relative = PurePosixPath(name)
    if ".." in relative.parts:
        raise ValueError(f"document name must not contain '..': '{name}'")
    if not relative.suffix:
        raise ValueError(f"document name must have a file extension: '{name}'")
    return relative
