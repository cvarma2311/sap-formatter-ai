import json
from pathlib import Path
from typing import Any, Optional


class LocalCache:
    """
    Simple file-backed cache for deterministic agent outputs.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({})

    def _read(self) -> dict:
        with self.path.open() as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with self.path.open("w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def get(self, key: str) -> Optional[Any]:
        data = self._read()
        return data.get(key)

    def set(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

