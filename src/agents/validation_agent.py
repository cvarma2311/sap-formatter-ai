import re
from typing import Optional, Tuple, List

from src.data_models import ConstraintSpec, DataType, MappingRule, ValidationFunction
from src.normalization.type_normalizer import normalize_type


RANGE_PATTERN = re.compile(r"(?:between|from)\s+([-+]?\d+(?:\.\d+)?)\s+(?:and|to)\s+([-+]?\d+(?:\.\d+)?)", re.IGNORECASE)
ALLOWED_PATTERN = re.compile(r"(?:allowed values|must be one of|in:?)\s*([A-Za-z0-9_,\s-]+)", re.IGNORECASE)
REGEX_PATTERN = re.compile(r"(?:pattern|regex)[:\s]+(.+)", re.IGNORECASE)


def _select_validation_function(description: str) -> ValidationFunction:
    desc = description.lower()
    if "must be one of" in desc or "allowed values" in desc or "lookup" in desc:
        return ValidationFunction.IN
    if "pattern" in desc or "regex" in desc or "format" in desc:
        return ValidationFunction.REGEX
    if "between" in desc or "range" in desc:
        return ValidationFunction.RANGE
    if "not blank" in desc or "not null" in desc or "required" in desc:
        return ValidationFunction.NOT_NULL
    return ValidationFunction.EQUAL


def _parse_allowed(description: str) -> Optional[List[str]]:
    if not description:
        return None
    match = ALLOWED_PATTERN.search(description)
    if not match:
        return None
    raw = match.group(1)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or None


def _parse_range(description: str) -> Tuple[Optional[float], Optional[float]]:
    if not description:
        return None, None
    match = RANGE_PATTERN.search(description)
    if not match:
        return None, None
    try:
        return float(match.group(1)), float(match.group(2))
    except ValueError:
        return None, None


def _parse_pattern(description: str) -> Optional[str]:
    if not description:
        return None
    match = REGEX_PATTERN.search(description)
    if not match:
        return None
    return match.group(1).strip()


def build_validation(rule: MappingRule) -> Tuple[DataType, ValidationFunction, Optional[ConstraintSpec]]:
    data_type = normalize_type(rule.type)
    validation_fn = _select_validation_function(rule.description or "")
    allowed_values = _parse_allowed(rule.description or "")
    range_min, range_max = _parse_range(rule.description or "")
    pattern = _parse_pattern(rule.description or "")
    constraints = None
    if any(
        [
            rule.required is not None,
            rule.max_length is not None,
            rule.severity is not None,
            allowed_values,
            pattern,
            range_min is not None,
            range_max is not None,
        ]
    ):
        constraints = ConstraintSpec(
            required=rule.required,
            max_length=rule.max_length,
            severity=rule.severity,
            allowed_values=allowed_values,
            pattern=pattern,
            range_min=range_min,
            range_max=range_max,
        )
    return data_type, validation_fn, constraints
