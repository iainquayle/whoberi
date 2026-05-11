import hashlib
import json


def row_hash(row: dict) -> str:
    serializable = {k: str(v) for k, v in row.items()}
    return hashlib.sha256(json.dumps(serializable, sort_keys=True).encode()).hexdigest()
