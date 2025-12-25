from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from pydantic import ValidationError

from src.data_models import MappingRule
from src.utils.hashing import hash_dict
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _load_raw_rules(path: Path) -> List[dict]:
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    if isinstance(data, dict) and "rules" in data:
        return data.get("rules") or []
    if isinstance(data, list):
        return data
    raise ValueError("YAML structure must be a list or contain a top-level 'rules' key.")


def load_rules(path: Path, rule_id: Optional[str] = None) -> Tuple[List[MappingRule], str]:
    """
    Load YAML rules into MappingRule models.
    Returns tuple of rules list and deterministic input hash.
    """
    raw_rules = _load_raw_rules(path)
    if rule_id:
        raw_rules = [r for r in raw_rules if str(r.get("id")) == str(rule_id)]
        if not raw_rules:
            logger.warning("No rules found matching id=%s", rule_id)
    parsed: List[MappingRule] = []
    for entry in raw_rules:
        if not entry.get("target"):
            logger.warning("Skipping mapping rule %s: missing target", entry.get("id"))
            continue
        try:
            parsed.append(MappingRule.model_validate(entry))
        except ValidationError as exc:
            logger.error("Invalid mapping rule %s: %s", entry.get("id"), exc)
            continue
    input_hash = hash_dict(raw_rules)
    return parsed, input_hash
