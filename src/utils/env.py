import os
from pathlib import Path


def load_env_file(path: Path = Path(".env")) -> None:
    """
    Lightweight .env loader. Does not override existing environment variables.
    """
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)

