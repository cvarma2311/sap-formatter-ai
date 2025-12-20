from typing import List, Optional

from src.data_models import (
    ConstraintSpec,
    DataType,
    FieldRule,
    FieldRuleConfig,
    KeyConfig,
    SourceTargetSpec,
    TransformationConfig,
    TransformationType,
    ValidationFunction,
    LookupEntry,
    FilterEntry,
)
from src.normalization.id_normalizer import make_unique_id


def assemble_field_rule(
    table_name: str,
    field_name: str,
    target_table: str,
    target_field: str,
    data_type: DataType,
    validation_function: ValidationFunction,
    constraints: Optional[ConstraintSpec],
    transformations: List[TransformationConfig | TransformationType],
    lookups: List[LookupEntry],
    filters: List[FilterEntry],
    relation_keys: str,
) -> FieldRule:
    source_spec = SourceTargetSpec(
        table=table_name, field=field_name, lookups=lookups, filters=filters, transformations=transformations
    )
    target_spec = SourceTargetSpec(
        table=target_table, field=target_field, lookups=[], filters=[], transformations=[]
    )
    key_config = KeyConfig(validation_function=validation_function, source=source_spec, target=target_spec)
    config = FieldRuleConfig(key_config=key_config, constraints=constraints)
    unique_id = make_unique_id(table_name, field_name)
    return FieldRule(
        unique_id=unique_id,
        table_name=table_name,
        field_name=field_name,
        relation_keys=relation_keys,
        data_type=data_type,
        config=config,
    )
