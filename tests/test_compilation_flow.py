from pathlib import Path

from src.orchestration.rule_graph import compile_rules_with_cache
from src.rule_loader import load_rules


def test_compile_single_rule_no_cache():
    rules, input_hash = load_rules(Path("data/agile_mdg_rules.yaml"), rule_id="M-001")
    assert rules, "Expected at least one rule with id M-001 in sample YAML"
    catalog, debug_traces = compile_rules_with_cache(
        rules,
        validation_description="Test Validation",
        input_hash=input_hash,
        cache_dir=None,
        use_cache=False,
        debug=False,
    )
    # Expect either field or procedural outputs
    assert catalog.field_rules or catalog.procedural_rules
    # Deterministic ids present
    if catalog.field_rules:
        assert catalog.field_rules[0].unique_id
    assert debug_traces == []
