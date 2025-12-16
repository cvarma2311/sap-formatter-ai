from typing import List, Optional

from src.data_models import (
    Catalog,
    FieldRule,
    MappingRule,
    ProceduralRule,
    RuleIntent,
)


class RuleCompileState:
    """
    Shared state passed between agents during compilation.
    """

    def __init__(self, mapping_rule: MappingRule, intent: RuleIntent):
        self.mapping_rule = mapping_rule
        self.intent = intent
        self.identity_part: Optional[tuple[str, str]] = None
        self.relation_key: Optional[str] = None
        self.validation_part: Optional[tuple] = None
        self.transformations: Optional[list] = None
        self.procedural_ir: Optional[tuple] = None
        self.compiled_rules: List[FieldRule | ProceduralRule] = []
        self.errors: List[str] = []
        self.catalog: Optional[Catalog] = None

