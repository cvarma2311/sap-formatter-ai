import hashlib
import json
from typing import Any


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_dict(data: Any) -> str:
    """
    Deterministically hash any JSON-serializable structure.
    """
    normalized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hash_text(normalized)

