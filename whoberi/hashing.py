import hashlib


def row_hash(row: dict) -> str:
    key = "|".join(f"{k}={v}" for k, v in sorted(row.items()))
    return hashlib.sha256(key.encode()).hexdigest()
