from dataclasses import dataclass

Payload = str | bytes | bytearray | memoryview  # exhaustively matched by the sink


@dataclass(frozen=True)
class Document:
    name: str      # relative path including extension: "invoices/2026-01-fooco.pdf"
    payload: Payload
