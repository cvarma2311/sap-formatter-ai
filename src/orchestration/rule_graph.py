from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from src.agents.chunking_agent import normalize_chunking
from src.agents.defaulting_agent import normalize_defaults
from src.agents.identity_agent import resolve_identity
from src.agents.intent_classifier import classify_intent
from src.agents.multitarget_agent import build_multitarget_specs
from src.agents.procedural_ir_agent import build_procedural_ir
from src.agents.relation_agent import resolve_relation
from src.agents.repair_agent import attempt_repair
from src.agents.transformation_agent import resolve_transformations
from src.agents.validation_agent import build_validation
from src.assembler.catalog_assembler import assemble_catalog
from src.assembler.field_rule_assembler import assemble_field_rule
from src.assembler.procedural_rule_assembler import assemble_procedural_rule
from src.data_models import (
    Catalog,
    ConstraintSpec,
    DataType,
    FieldRule,
    MappingRule,
    ProceduralRule,
    RuleIntent,
    SourceTargetSpec,
    TransformationType,
    ValidationFunction,
)
from src.normalization.relation_normalizer import make_relation_key
from src.utils.cache import LocalCache
from src.utils.hashing import hash_text
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RuleState(TypedDict, total=False):
    rule: MappingRule
    intent: RuleIntent | None
    identity: Tuple[str, str] | None
    relation_key: str | None
    validation: Tuple[DataType, ValidationFunction, ConstraintSpec | None] | None
    transformations: List[TransformationType]
    transform_issues: List[str]
    field_rules: List[FieldRule]
    procedural_rules: List[ProceduralRule]


def _intent_with_cache(rule: MappingRule, cache: Optional[LocalCache]) -> Tuple[RuleIntent, dict]:
    key = hash_text((rule.description or "") + (rule.xpath or "") + (rule.target.field or ""))
    if cache:
        cached = cache.get(key)
        if cached:
            return RuleIntent(cached["intent"]), cached
    intent, meta = classify_intent(rule)
    if cache:
        cache.set(key, {"intent": intent.value, **meta})
    return intent, meta


def _transformations_with_cache(description: str, cache: Optional[LocalCache]):
    key = hash_text(description)
    if cache:
        cached = cache.get(key)
        if cached:
            return [t for t in cached.get("transformations", [])], cached.get("issues", [])
    transformations, issues = resolve_transformations(description)
    if cache:
        cache.set(
            key,
            {"transformations": [t.value if hasattr(t, "value") else str(t) for t in transformations], "issues": issues},
        )
    return transformations, issues


def _build_graph(intent_cache: Optional[LocalCache], transform_cache: Optional[LocalCache]) -> StateGraph:
    graph: StateGraph = StateGraph(RuleState)

    def classify_node(state: RuleState) -> RuleState:
        intent, _ = _intent_with_cache(state["rule"], intent_cache)
        state["intent"] = intent
        return state

    def identity_node(state: RuleState) -> RuleState:
        table_name, field_name = resolve_identity(state["rule"])
        state["identity"] = (table_name, field_name)
        state["relation_key"] = resolve_relation(state["rule"])
        return state

    def validation_node(state: RuleState) -> RuleState:
        data_type, validation_fn, constraints = build_validation(state["rule"])
        state["validation"] = (data_type, validation_fn, constraints)
        return state

    def transformation_node(state: RuleState) -> RuleState:
        transformations_raw, issues = _transformations_with_cache(state["rule"].description or "", transform_cache)
        transformations = [
            t if isinstance(t, TransformationType) else TransformationType(t) for t in transformations_raw
        ]
        state["transformations"] = transformations
        state["transform_issues"] = issues
        for issue in issues:
            logger.warning("Rule %s needs review: %s", state["rule"].id, issue)
        return state

    def route_selector(state: RuleState) -> str:
        intent = state.get("intent")
        if intent == RuleIntent.PROCEDURAL_MAPPING:
            return "procedural"
        return "field"

    def build_procedural_node(state: RuleState) -> RuleState:
        rule = state["rule"]
        (table_name, field_name) = state["identity"]
        rule_type, cond, defaults, chunking, row_expansion, steps = build_procedural_ir(
            rule.description or "", source_field=rule.target.field or ""
        )
        defaults = normalize_defaults(defaults)
        chunking = normalize_chunking(chunking)
        source_spec = SourceTargetSpec(table=table_name, field=field_name)
        targets = [SourceTargetSpec(table=rule.target.structure, field=rule.target.field)]
        try:
            proc_rule = assemble_procedural_rule(
                rule_type=rule_type,
                condition=cond,
                source=source_spec,
                targets=targets,
                defaults=defaults,
                chunking=chunking,
                row_expansion=row_expansion,
                steps=steps,
            )
            state.setdefault("procedural_rules", []).append(proc_rule)
        except ValidationError as exc:
            repaired = attempt_repair(
                {
                    "rule_type": rule_type.value if hasattr(rule_type, "value") else str(rule_type),
                    "condition": cond.model_dump(),
                    "defaults": [d.model_dump() for d in defaults],
                    "row_expansion": row_expansion.model_dump() if row_expansion else None,
                },
                str(exc),
            )
            logger.error("Procedural rule validation failed for %s: %s", rule.id, exc)
            logger.error("Repaired fragment (NEEDS_REVIEW): %s", repaired)
        return state

    def build_field_node(state: RuleState) -> RuleState:
        rule = state["rule"]
        (table_name, field_name) = state["identity"]
        relation_key = state["relation_key"]
        data_type, validation_fn, constraints = state["validation"]
        transformations = state.get("transformations") or []

        primary_target, additional_targets = build_multitarget_specs(
            rule.target.structure or table_name,
            rule.target.field or field_name,
            rule.description or "",
        )

        def append_field(target_table: str | None, target_field: str | None, rel_key: str | None):
            try:
                fr = assemble_field_rule(
                    table_name=table_name,
                    field_name=field_name,
                    target_table=target_table or "",
                    target_field=target_field or "",
                    data_type=data_type,
                    validation_function=validation_fn,
                    constraints=constraints,
                    transformations=transformations,
                    relation_keys=rel_key or "",
                )
                state.setdefault("field_rules", []).append(fr)
            except ValidationError as exc:
                repaired = attempt_repair(
                    {
                        "table_name": table_name,
                        "field_name": field_name,
                        "target_table": target_table,
                        "target_field": target_field,
                        "data_type": data_type.value if hasattr(data_type, "value") else str(data_type),
                    },
                    str(exc),
                )
                logger.error("Field rule validation failed for %s: %s", rule.id, exc)
                logger.error("Repaired fragment (NEEDS_REVIEW): %s", repaired)

        append_field(primary_target.table, primary_target.field, relation_key or make_relation_key(primary_target.table, primary_target.field))
        for tgt in additional_targets:
            append_field(tgt.table, tgt.field, make_relation_key(tgt.table, tgt.field))

        return state

    graph.add_node("classify_intent", classify_node)
    graph.add_node("identity", identity_node)
    graph.add_node("validation", validation_node)
    graph.add_node("transformations", transformation_node)
    graph.add_node("route", lambda s: s)
    graph.add_node("build_procedural", build_procedural_node)
    graph.add_node("build_field", build_field_node)

    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "identity")
    graph.add_edge("identity", "validation")
    graph.add_edge("validation", "transformations")
    graph.add_edge("transformations", "route")
    graph.add_conditional_edges(
        "route",
        route_selector,
        {
            "procedural": "build_procedural",
            "field": "build_field",
        },
    )
    graph.add_edge("build_procedural", END)
    graph.add_edge("build_field", END)
    return graph


def compile_rules(
    rules: List[MappingRule],
    validation_description: str | None,
    input_hash: str | None,
) -> Catalog:
    catalog, _ = compile_rules_with_cache(
        rules, validation_description, input_hash, cache_dir=Path(".cache"), use_cache=True, debug=False
    )
    return catalog


def compile_rules_with_cache(
    rules: List[MappingRule],
    validation_description: str | None,
    input_hash: str | None,
    cache_dir: Path | None,
    use_cache: bool,
    debug: bool = False,
) -> Tuple[Catalog, List[Dict[str, Any]]]:
    intent_cache = LocalCache(cache_dir / "intent_cache.json") if use_cache and cache_dir else None
    transform_cache = LocalCache(cache_dir / "transform_cache.json") if use_cache and cache_dir else None

    graph = _build_graph(intent_cache, transform_cache)
    app = graph.compile()

    field_rules: List[FieldRule] = []
    procedural_rules: List[ProceduralRule] = []
    debug_traces: List[Dict[str, Any]] = []

    for rule in rules:
        initial_state: RuleState = {
            "rule": rule,
            "intent": None,
            "identity": None,
            "relation_key": None,
            "validation": None,
            "transformations": [],
            "transform_issues": [],
            "field_rules": [],
            "procedural_rules": [],
        }
        if debug:
            result = app.invoke(initial_state, debug=True)
            if isinstance(result, dict) and "state" in result:
                final_state: RuleState = result["state"]
                dbg = result.get("__debug__") or result.get("debug")
            else:
                final_state = result  # type: ignore
                dbg = final_state.get("__debug__") if isinstance(final_state, dict) else None
            if dbg:
                debug_traces.append({"rule_id": rule.id, "debug": dbg})
        else:
            final_state: RuleState = app.invoke(initial_state)
        field_rules.extend(final_state.get("field_rules", []))
        procedural_rules.extend(final_state.get("procedural_rules", []))

    catalog = assemble_catalog(field_rules, procedural_rules, validation_description, input_hash)
    return catalog, debug_traces
