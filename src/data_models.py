from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    ERROR = "E"
    WARNING = "W"
    INFO = "I"


class RuleIntent(str, Enum):
    SIMPLE_FIELD_RULE = "SIMPLE_FIELD_RULE"
    MULTI_TARGET_MAP = "MULTI_TARGET_MAP"
    PROCEDURAL_MAPPING = "PROCEDURAL_MAPPING"
    LOOKUP_RULE = "LOOKUP_RULE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    BOOLEAN = "boolean"
    UNKNOWN = "unknown"


class ValidationFunction(str, Enum):
    EQUAL = "equal"
    IN = "in"
    REGEX = "regex"
    RANGE = "range"
    NOT_NULL = "not_null"
    NONE = "none"


class RuleType(str, Enum):
    DEFAULTING = "DEFAULTING"
    TEXT_CHUNKING = "TEXT_CHUNKING"
    MULTI_TARGET_MAP = "MULTI_TARGET_MAP"
    TEXT_DEFAULTS_AND_CHUNKING = "TEXT_DEFAULTS_AND_CHUNKING"
    DEFAULTING_ONLY = "DEFAULTING_ONLY"
    CONDITIONAL_DEFAULTS = "CONDITIONAL_DEFAULTS"
    ROW_EXPANSION = "ROW_EXPANSION"
    GENERIC_PROCEDURAL = "GENERIC_PROCEDURAL"


class ConditionType(str, Enum):
    ALWAYS = "ALWAYS"
    NOT_BLANK = "NOT_BLANK"
    IS_BLANK = "IS_BLANK"


class TransformationType(str, Enum):
    NOT_NULL = "not_null"
    TRIM = "trim"
    UPPER = "upper"
    PAD_LEFT = "pad_left"
    SUBSTRING = "substring"
    NEEDS_REVIEW = "needs_review"


class TargetRef(BaseModel):
    structure: Optional[str] = None
    field: Optional[str] = None


class MappingRule(BaseModel):
    id: str
    name: Optional[str] = None
    source_field: Optional[str] = None
    xpath: Optional[str] = None
    type: Optional[str] = None
    required: Optional[bool] = None
    max_length: Optional[int] = None
    severity: Optional[SeverityLevel] = None
    description: Optional[str] = None
    target: TargetRef


class SourceTargetSpec(BaseModel):
    table: Optional[str] = None
    field: Optional[str] = None
    transformations: List[TransformationType] = Field(default_factory=list)


class ConstraintSpec(BaseModel):
    required: Optional[bool] = None
    max_length: Optional[int] = None
    severity: Optional[SeverityLevel] = None
    allowed_values: Optional[List[str]] = None
    pattern: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None


class KeyConfig(BaseModel):
    validation_function: ValidationFunction = ValidationFunction.NONE
    source: SourceTargetSpec
    target: SourceTargetSpec


class FieldRuleConfig(BaseModel):
    key_config: KeyConfig
    constraints: Optional[ConstraintSpec] = None


class FieldRule(BaseModel):
    unique_id: str
    table_name: str
    field_name: str
    relation_keys: str
    data_type: DataType = DataType.UNKNOWN
    config: FieldRuleConfig


class Condition(BaseModel):
    type: ConditionType = ConditionType.ALWAYS
    field: Optional[str] = None


class DefaultAssignment(BaseModel):
    field: str
    value: str


class ChunkingSpec(BaseModel):
    chunk_size: int
    ordinal_start: int = 1
    ordinal_increment: int = 1
    map_to: Optional[str] = None


class RowExpansionSpec(BaseModel):
    delimiter: Optional[str] = None
    map_to: Optional[str] = None


class ProceduralRule(BaseModel):
    rule_type: RuleType
    condition: Condition = Condition()
    source: Optional[SourceTargetSpec] = None
    targets: List[SourceTargetSpec] = Field(default_factory=list)
    defaults: List[DefaultAssignment] = Field(default_factory=list)
    chunking: Optional[ChunkingSpec] = None
    row_expansion: Optional[RowExpansionSpec] = None
    steps: List[str] = Field(default_factory=list)


class CatalogMetadata(BaseModel):
    schema_version: str = "0.1.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    compiler_version: str = "0.1.0"
    input_hash: Optional[str] = None


class Catalog(BaseModel):
    validation_description: Optional[str] = None
    field_rules: List[FieldRule] = Field(default_factory=list)
    procedural_rules: List[ProceduralRule] = Field(default_factory=list)
    metadata: CatalogMetadata = Field(default_factory=CatalogMetadata)


__all__ = [
    "Catalog",
    "CatalogMetadata",
    "ChunkingSpec",
    "Condition",
    "ConditionType",
    "ConstraintSpec",
    "DataType",
    "DefaultAssignment",
    "FieldRule",
    "FieldRuleConfig",
    "KeyConfig",
    "MappingRule",
    "ProceduralRule",
    "RuleIntent",
    "RuleType",
    "SeverityLevel",
    "SourceTargetSpec",
    "TargetRef",
    "TransformationType",
    "ValidationFunction",
    "RowExpansionSpec",
]
