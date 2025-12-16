from src.data_models import MappingRule
from src.normalization.relation_normalizer import make_relation_key


def resolve_relation(rule: MappingRule) -> str:
    return make_relation_key(rule.target.structure, rule.target.field)

