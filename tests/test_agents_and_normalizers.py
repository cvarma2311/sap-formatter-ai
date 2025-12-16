from pathlib import Path

from src.agents.procedural_ir_agent import build_procedural_ir
from src.agents.transformation_agent import resolve_transformations
from src.agents.validation_agent import build_validation
from src.data_models import ConditionType, DataType, MappingRule, TargetRef
from src.normalization.type_normalizer import normalize_type


def test_type_normalizer_basic():
    assert normalize_type("CHAR") == DataType.STRING
    assert normalize_type("NUMC") == DataType.INTEGER
    assert normalize_type("DEC") == DataType.DECIMAL
    assert normalize_type(None) == DataType.UNKNOWN


def test_validation_agent_parses_range_and_allowed():
    rule = MappingRule(
        id="T-001",
        description="Value must be one of A,B or between 1 and 10",
        type="NUMC",
        target=TargetRef(structure="X", field="Y"),
    )
    data_type, validation_fn, constraints = build_validation(rule)
    assert data_type == DataType.INTEGER
    assert constraints is not None
    assert constraints.allowed_values == ["A", "B"]
    assert constraints.range_min == 1.0
    assert constraints.range_max == 10.0


def test_transformation_agent_detects_known_fragments():
    transformations, issues = resolve_transformations("trim and uppercase if not blank")
    assert issues == []
    assert transformations  # contains TRIM and UPPER
    assert any(t.value == "trim" for t in transformations)
    assert any(t.value == "upper" for t in transformations)


def test_procedural_ir_defaults_and_chunking():
    rule_type, cond, defaults, chunking, row_expansion, steps = build_procedural_ir(
        "Default TextExistsIndicator=X when MATERIAL_BASIC_TEXT not blank; split 72 chars increment 1",
        source_field="SAPScriptLineText",
    )
    assert cond.type == ConditionType.NOT_BLANK
    assert defaults
    assert chunking and chunking.chunk_size == 72
    assert "apply_defaults" in steps and "add_ordinal_sequence" in steps
    assert rule_type.value in {"TEXT_DEFAULTS_AND_CHUNKING", "CONDITIONAL_DEFAULTS"}
    assert row_expansion is None


def test_procedural_ir_row_expansion_with_delimiter():
    rule_type, cond, defaults, chunking, row_expansion, steps = build_procedural_ir(
        "Expand to rows separated by '|' for each line", source_field="LongText"
    )
    assert rule_type.value == "ROW_EXPANSION"
    assert row_expansion is not None
    assert row_expansion.delimiter == "|"
    assert "row_expansion" in steps
