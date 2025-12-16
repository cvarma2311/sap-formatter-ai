from typing import List, Optional

from src.data_models import (
    ChunkingSpec,
    Condition,
    DefaultAssignment,
    ProceduralRule,
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
    steps: List[str],
) -> ProceduralRule:
    return ProceduralRule(
        rule_type=rule_type,
        condition=condition,
        source=source,
        targets=targets,
        defaults=defaults,
        chunking=chunking,
        steps=steps,
    )

