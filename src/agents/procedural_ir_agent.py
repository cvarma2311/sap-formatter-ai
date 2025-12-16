import re
from typing import List, Tuple

from src.data_models import ChunkingSpec, Condition, ConditionType, DefaultAssignment, RowExpansionSpec, RuleType

CHUNK_PATTERN = re.compile(r"(?:split|chunk|first)\s*(\d+)", re.IGNORECASE)
ORDINAL_PATTERN = re.compile(r"(?:ordinal|increment)\s*(\d+)", re.IGNORECASE)
CONDITION_PATTERN = re.compile(r"when\s+([A-Za-z0-9_]+)\s+not\s+blank", re.IGNORECASE)
DEFAULT_PATTERN = re.compile(r"([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9*]+)")
ROW_EXPANSION_PATTERN = re.compile(r"(row expansion|expand to rows|row\-expansion|one row per|each line)", re.IGNORECASE)
DELIMITER_PATTERN = re.compile(r"(?:split|separated)\s+by\s+['\"]?([^'\"\\s]+)['\"]?", re.IGNORECASE)


def build_procedural_ir(
    description: str, source_field: str = ""
) -> Tuple[RuleType, Condition, List[DefaultAssignment], ChunkingSpec | None, RowExpansionSpec | None, List[str]]:
    desc = description or ""
    defaults: List[DefaultAssignment] = []
    for key, value in DEFAULT_PATTERN.findall(desc):
        defaults.append(DefaultAssignment(field=key, value=value))

    chunk_size = None
    if match := CHUNK_PATTERN.search(desc):
        chunk_size = int(match.group(1))
    ordinal_inc = 1
    if match := ORDINAL_PATTERN.search(desc):
        ordinal_inc = int(match.group(1))

    chunking = None
    if chunk_size:
        chunking = ChunkingSpec(chunk_size=chunk_size, ordinal_start=1, ordinal_increment=ordinal_inc, map_to=source_field)

    row_expansion = None
    delimiter = None
    if match := DELIMITER_PATTERN.search(desc):
        delimiter = match.group(1)
    if ROW_EXPANSION_PATTERN.search(desc) or delimiter:
        row_expansion = RowExpansionSpec(delimiter=delimiter, map_to=source_field)

    cond = Condition(type=ConditionType.ALWAYS)
    if match := CONDITION_PATTERN.search(desc):
        cond = Condition(type=ConditionType.NOT_BLANK, field=match.group(1))

    steps: List[str] = []
    if defaults:
        steps.append("apply_defaults")
    if chunking:
        steps.append("chunk_text")
        steps.append("add_ordinal_sequence")
    if row_expansion:
        steps.append("row_expansion")
        if delimiter:
            steps.append("split_by_delimiter")

    if row_expansion and defaults:
        rule_type = RuleType.ROW_EXPANSION
    elif row_expansion:
        rule_type = RuleType.ROW_EXPANSION
    elif defaults and chunking:
        rule_type = RuleType.TEXT_DEFAULTS_AND_CHUNKING
    elif chunking:
        rule_type = RuleType.TEXT_CHUNKING
    elif defaults and cond.type == ConditionType.NOT_BLANK:
        rule_type = RuleType.CONDITIONAL_DEFAULTS
    elif defaults:
        rule_type = RuleType.DEFAULTING_ONLY
    else:
        rule_type = RuleType.GENERIC_PROCEDURAL

    return rule_type, cond, defaults, chunking, row_expansion, steps
