import re
from typing import Iterable, List, Tuple

from src.data_models import TransformationType


PAD_PATTERN = re.compile(r"pad(?:\s+left)?\s*(?:to)?\s*(\d+)", re.IGNORECASE)
PAD_RIGHT_PATTERN = re.compile(r"pad\s+right\s*(?:to)?\s*(\d+)", re.IGNORECASE)
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
        elif "lower" in frag:
            normalized.append(TransformationType.LOWER)
        elif "concat" in frag or "concatenate" in frag:
            normalized.append(TransformationType.CONCAT)
        elif "is text" in frag or "is_text" in frag:
            normalized.append(TransformationType.IS_TEXT)
        elif "is number" in frag or "is_number" in frag:
            normalized.append(TransformationType.IS_NUMBER)
        elif (match := PAD_PATTERN.search(frag)):
            normalized.append(TransformationType.PAD_LEFT)
        elif (match := PAD_RIGHT_PATTERN.search(frag)):
            normalized.append(TransformationType.PAD_RIGHT)
        elif (match := SUBSTRING_PATTERN.search(frag)):
            normalized.append(TransformationType.SUBSTRING)
        elif "add" in frag:
            normalized.append(TransformationType.ADD)
        elif "subtract" in frag:
            normalized.append(TransformationType.SUBTRACT)
        elif "multiply" in frag:
            normalized.append(TransformationType.MULTIPLY)
        elif "divide" in frag:
            normalized.append(TransformationType.DIVIDE)
        elif "round" in frag:
            normalized.append(TransformationType.ROUND)
        elif "coalesce" in frag:
            normalized.append(TransformationType.COALESCE)
        else:
            unknown.append(fragment)
    return normalized, unknown
