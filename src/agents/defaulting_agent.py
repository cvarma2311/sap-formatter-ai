from typing import List

from src.data_models import DefaultAssignment


def normalize_defaults(defaults: List[DefaultAssignment]) -> List[DefaultAssignment]:
    # Ensure values are strings and strip whitespace.
    normalized = []
    for item in defaults:
        normalized.append(DefaultAssignment(field=item.field.strip(), value=str(item.value).strip()))
    return normalized

