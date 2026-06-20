"""Cross-ledger source-row accessor handed to handlers as `books`.

Holds ledger paths only — never contents — so absolute memory overhead stays
flat regardless of book size. `rows(name)` returns a fresh streaming reader per
call; reads fire at handler-call time and funnel through `delimited_io`.
"""
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
        """Stream another ledger's raw source rows by its ledgers-relative stem.

        Source rows are static input — order-independent, no eval ordering. Not
        cached: call again to re-iterate (re-reads the file), or `list(...)` to
        materialize and own the memory. Unknown name raises, listing available.
        """
        try:
            path = self._paths[name]
        except KeyError:
            avail = ", ".join(sorted(self._paths)) or "(none)"
            raise KeyError(f"unknown book '{name}' — available: {avail}") from None
        return read_rows(path)              # fresh streaming reader; never cached
