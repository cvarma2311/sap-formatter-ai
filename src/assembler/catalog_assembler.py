from typing import List

from src.data_models import Catalog, CatalogMetadata, FieldRule, LookupEntry, ProceduralRule
from src.normalization.id_normalizer import sort_field_rules


def assemble_catalog(
    field_rules: List[FieldRule],
    procedural_rules: List[ProceduralRule],
    lookups: List[LookupEntry],
    validation_description: str | None,
    input_hash: str | None,
) -> Catalog:
    sorted_fields = sort_field_rules(field_rules)
    sorted_procedural = sorted(procedural_rules, key=lambda r: (r.rule_type, r.condition.type.name if r.condition else ""))  # type: ignore
    metadata = CatalogMetadata(input_hash=input_hash)
    return Catalog(
        validation_description=validation_description,
        field_rules=sorted_fields,
        procedural_rules=sorted_procedural,
        lookups=lookups,
        metadata=metadata,
    )
