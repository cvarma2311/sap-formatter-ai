import re
from pathlib import Path
from typing import List, Tuple

from src.data_models import (
    LookupEntry,
    LookupOperator,
    LookupRuleType,
    LookupSourceType,
)
from src.utils.csv_field_matcher import best_header_match

DEFAULT_PATTERN = re.compile(r"(?:default\s+)?([A-Za-z0-9_]+)\s+as\s+'([^']+)'", re.IGNORECASE)
EXPECTED_PATTERN = re.compile(r"(?:map\s+the\s+attribute\s+value\s+in\s+|expect\s+)([A-Za-z0-9_]+)", re.IGNORECASE)
ARROW_PATTERN = re.compile(r"\(([^)]+)\)")


def _parse_fields_from_arrow(text: str) -> Tuple[str | None, str | None]:
    """
    Extract table/field from patterns like (Product->QuantityCharacteristic->Quantity)
    """
    match = ARROW_PATTERN.search(text)
    if not match:
        return None, None
    segments = [seg.strip() for seg in match.group(1).split("->") if seg.strip()]
    if not segments:
        return None, None
    table = segments[0] if segments else None
    field = segments[-1] if segments else None
    return table, field


def parse_lookup_entries(description: str, csv_path: Path | None = None) -> List[LookupEntry]:
    desc = description or ""
    entries: List[LookupEntry] = []

    # Defaults: "Default Quantity as 'EA'"
    for field, value in DEFAULT_PATTERN.findall(desc):
        table, inferred_field = _parse_fields_from_arrow(desc)
        matched = None
        if csv_path and inferred_field:
            matched = best_header_match(csv_path, inferred_field)
        entries.append(
            LookupEntry(
                rule_type=LookupRuleType.DEFAULT,
                source_type=LookupSourceType.CSV_HINT if matched else LookupSourceType.TABLE,
                table=table,
                field=matched or inferred_field or field,
                cond_value=value,
                operator=LookupOperator.NONE,
                expected_result=None,
            )
        )

    # Expected values or dynamic mapping: "Map the attribute value in unitCode"
    for expected_field in EXPECTED_PATTERN.findall(desc):
        table, inferred_field = _parse_fields_from_arrow(desc)
        matched = None
        if csv_path and inferred_field:
            matched = best_header_match(csv_path, inferred_field)
        entries.append(
            LookupEntry(
                rule_type=LookupRuleType.EXPECTED,
                source_type=LookupSourceType.CSV_HINT if matched else LookupSourceType.TABLE,
                table=table,
                field=matched or inferred_field or expected_field,
                cond_value=None,
                operator=LookupOperator.NONE,
                expected_result="ATTRIBUTE_VALUE",
            )
        )

    return entries
