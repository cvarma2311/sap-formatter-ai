from typing import Optional, Tuple

from src.data_models import ConstraintSpec, DataType, MappingRule, ValidationFunction
from src.normalization.type_normalizer import normalize_type


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


def build_validation(rule: MappingRule) -> Tuple[DataType, ValidationFunction, Optional[ConstraintSpec]]:
    data_type = normalize_type(rule.type)
    validation_fn = _select_validation_function(rule.description or "")
    constraints = None
    if any([rule.required is not None, rule.max_length is not None, rule.severity is not None]):
        constraints = ConstraintSpec(
            required=rule.required,
            max_length=rule.max_length,
            severity=rule.severity,
        )
    return data_type, validation_fn, constraints

