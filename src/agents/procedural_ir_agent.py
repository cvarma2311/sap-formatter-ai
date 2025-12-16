import re
from typing import List, Tuple

from src.data_models import ChunkingSpec, Condition, ConditionType, DefaultAssignment, SourceTargetSpec

CHUNK_PATTERN = re.compile(r"(?:split|chunk|first)\s*(\d+)", re.IGNORECASE)
ORDINAL_PATTERN = re.compile(r"(?:ordinal|increment)\s*(\d+)", re.IGNORECASE)
CONDITION_PATTERN = re.compile(r"when\s+([A-Za-z0-9_]+)\s+not\s+blank", re.IGNORECASE)
DEFAULT_PATTERN = re.compile(r"([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9*]+)")


def build_procedural_ir(description: str, source_field: str = "") -> Tuple[Condition, List[DefaultAssignment], ChunkingSpec | None]:
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

    cond = Condition(type=ConditionType.ALWAYS)
    if match := CONDITION_PATTERN.search(desc):
        cond = Condition(type=ConditionType.NOT_BLANK, field=match.group(1))

    return cond, defaults, chunking

