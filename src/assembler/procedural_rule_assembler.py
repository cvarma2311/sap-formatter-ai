from typing import List, Optional

from src.data_models import (
    ChunkingSpec,
    Condition,
    DefaultAssignment,
    ProceduralRule,
    RowExpansionSpec,
    RuleType,
    SourceTargetSpec,
)


def assemble_procedural_rule(
    rule_type: RuleType,
    condition: Condition,
    source: Optional[SourceTargetSpec],
    targets: List[SourceTargetSpec],
    defaults: List[DefaultAssignment],
    chunking: Optional[ChunkingSpec],
    row_expansion: Optional[RowExpansionSpec],
    steps: List[str],
) -> ProceduralRule:
    return ProceduralRule(
        rule_type=rule_type,
        condition=condition,
        source=source,
        targets=targets,
        defaults=defaults,
        chunking=chunking,
        row_expansion=row_expansion,
        steps=steps,
    )
