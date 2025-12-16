import re
from typing import Iterable, List, Tuple

from src.data_models import TransformationType


PAD_PATTERN = re.compile(r"pad(?:\s+left)?\s*(?:to)?\s*(\d+)", re.IGNORECASE)
SUBSTRING_PATTERN = re.compile(r"(?:first|substring)\s*(\d+)", re.IGNORECASE)


def normalize_transformations(text_fragments: Iterable[str]) -> Tuple[List[TransformationType], List[str]]:
    normalized: List[TransformationType] = []
    unknown: List[str] = []
    for fragment in text_fragments:
        frag = fragment.lower().strip()
        if not frag:
            continue
        if "not blank" in frag or "required" in frag:
            normalized.append(TransformationType.NOT_NULL)
        elif "trim" in frag:
            normalized.append(TransformationType.TRIM)
        elif "upper" in frag:
            normalized.append(TransformationType.UPPER)
        elif (match := PAD_PATTERN.search(frag)):
            normalized.append(TransformationType.PAD_LEFT)
        elif (match := SUBSTRING_PATTERN.search(frag)):
            normalized.append(TransformationType.SUBSTRING)
        else:
            unknown.append(fragment)
    return normalized, unknown
