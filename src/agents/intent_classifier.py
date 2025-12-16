import re
from typing import Dict, Tuple

from src.data_models import MappingRule, RuleIntent
from src.utils.hashing import hash_text


def classify_intent(rule: MappingRule) -> Tuple[RuleIntent, Dict[str, str]]:
    """
    Classify rule intent using lightweight heuristics.
    Returns (intent, metadata).
    """
    description = (rule.description or "").lower()
    meta = {"hash": hash_text(description + (rule.xpath or "") + (rule.target.field or ""))}

    if "additionally map" in description:
        intent = RuleIntent.MULTI_TARGET_MAP
        meta["rationale"] = "Detected 'additionally map' phrase."
    elif any(keyword in description for keyword in ["default", "when ", "if ", "chunk", "split", "ordinal", "72"]):
        intent = RuleIntent.PROCEDURAL_MAPPING
        meta["rationale"] = "Detected procedural keywords (default/chunk/ordinal)."
    elif "lookup" in description or "allowed values" in description or "t134" in description:
        intent = RuleIntent.LOOKUP_RULE
        meta["rationale"] = "Detected lookup phrasing."
    else:
        intent = RuleIntent.SIMPLE_FIELD_RULE
        meta["rationale"] = "Fallback to simple field mapping."
    return intent, meta

