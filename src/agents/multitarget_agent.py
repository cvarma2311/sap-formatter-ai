import re
from typing import List, Tuple

from src.data_models import SourceTargetSpec

ADDITIONAL_PATTERN = re.compile(r"additionally map.*?to\s+([A-Za-z0-9_]+)", re.IGNORECASE)


def detect_additional_targets(description: str, fallback_table: str = "") -> List[SourceTargetSpec]:
    matches = ADDITIONAL_PATTERN.findall(description or "")
    targets: List[SourceTargetSpec] = []
    for field in matches:
        targets.append(SourceTargetSpec(table=fallback_table or "Product", field=field))
    return targets


def build_multitarget_specs(
    primary_table: str,
    primary_field: str,
    description: str,
) -> Tuple[SourceTargetSpec, List[SourceTargetSpec]]:
    primary = SourceTargetSpec(table=primary_table, field=primary_field)
    additional = detect_additional_targets(description, fallback_table=primary_table)
    return primary, additional
