from typing import Optional


def make_relation_key(structure: Optional[str], field: Optional[str]) -> str:
    if not structure or not field:
        return ""
    return f"{structure}.{field}"

