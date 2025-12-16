import re
from typing import List, Tuple

from src.data_models import TransformationType
from src.normalization.transformation_normalizer import normalize_transformations


PAD_EXPLICIT = re.compile(r"pad(?:\s+left)?\s*(?:to)?\s*(\d+)", re.IGNORECASE)
SUBSTRING_EXPLICIT = re.compile(r"(?:first|substring)\s*(\d+)", re.IGNORECASE)


def extract_transformation_fragments(description: str) -> List[str]:
    desc = description.lower()
    fragments: List[str] = []
    if "not blank" in desc or "required" in desc:
        fragments.append("not blank")
    if "trim" in desc:
        fragments.append("trim")
    if "upper" in desc:
        fragments.append("upper")
    if PAD_EXPLICIT.search(description):
        fragments.append("pad")
    if SUBSTRING_EXPLICIT.search(description):
        fragments.append("substring")
    return fragments


def resolve_transformations(description: str) -> Tuple[List[TransformationType], List[str]]:
    """
    Returns transformations and issues (needs_review reasons).
    """
    fragments = extract_transformation_fragments(description)
    normalized = normalize_transformations(fragments)
    issues = []
    for frag, norm in zip(fragments, normalized):
        if norm == TransformationType.NEEDS_REVIEW:
            issues.append(f"Unrecognized transformation fragment: {frag}")
    return normalized, issues
