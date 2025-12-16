from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import ValidationError

from src.agents.repair_agent import attempt_repair
from src.agents.chunking_agent import normalize_chunking
from src.agents.defaulting_agent import normalize_defaults
from src.agents.identity_agent import resolve_identity
from src.agents.intent_classifier import classify_intent
from src.agents.multitarget_agent import build_multitarget_specs
from src.agents.procedural_ir_agent import build_procedural_ir
from src.agents.relation_agent import resolve_relation
from src.agents.transformation_agent import resolve_transformations
from src.agents.validation_agent import build_validation
from src.assembler.catalog_assembler import assemble_catalog
from src.assembler.field_rule_assembler import assemble_field_rule
from src.assembler.procedural_rule_assembler import assemble_procedural_rule
from src.data_models import Catalog, MappingRule, RuleIntent, RuleType, SourceTargetSpec, TransformationType
from src.normalization.relation_normalizer import make_relation_key
from src.utils.cache import LocalCache
from src.utils.hashing import hash_text
from src.utils.logging import get_logger

logger = get_logger(__name__)


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


def compile_rules(
    rules: List[MappingRule],
    validation_description: str | None,
    input_hash: str | None,
) -> Catalog:
    return compile_rules_with_cache(rules, validation_description, input_hash, cache_dir=Path(".cache"), use_cache=True)


def compile_rules_with_cache(
    rules: List[MappingRule],
    validation_description: str | None,
    input_hash: str | None,
    cache_dir: Path | None,
    use_cache: bool,
) -> Catalog:
    intent_cache = LocalCache(cache_dir / "intent_cache.json") if use_cache and cache_dir else None
    transform_cache = LocalCache(cache_dir / "transform_cache.json") if use_cache and cache_dir else None

    field_rules = []
    procedural_rules = []
    for rule in rules:
        intent, _ = _intent_with_cache(rule, intent_cache)
        table_name, field_name = resolve_identity(rule)
        relation_key = resolve_relation(rule)
        data_type, validation_fn, constraints = build_validation(rule)
        transformations_raw, issues = _transformations_with_cache(rule.description or "", transform_cache)
        transformations = [
            t if isinstance(t, TransformationType) else TransformationType(t) for t in transformations_raw
        ]
        for issue in issues:
            logger.warning("Rule %s needs review: %s", rule.id, issue)

        if intent == RuleIntent.PROCEDURAL_MAPPING:
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
                procedural_rules.append(proc_rule)
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
            continue

        primary_target, additional_targets = build_multitarget_specs(
            rule.target.structure or table_name,
            rule.target.field or field_name,
            rule.description or "",
        )

        # Primary mapping
        try:
            field_rules.append(
                assemble_field_rule(
                    table_name=table_name,
                    field_name=field_name,
                    target_table=primary_target.table or "",
                    target_field=primary_target.field or "",
                    data_type=data_type,
                    validation_function=validation_fn,
                    constraints=constraints,
                    transformations=transformations,
                    relation_keys=relation_key or make_relation_key(primary_target.table, primary_target.field),
                )
            )
        except ValidationError as exc:
            repaired = attempt_repair(
                {
                    "table_name": table_name,
                    "field_name": field_name,
                    "target_table": primary_target.table,
                    "target_field": primary_target.field,
                    "data_type": data_type.value if hasattr(data_type, "value") else str(data_type),
                },
                str(exc),
            )
            logger.error("Field rule validation failed for %s: %s", rule.id, exc)
            logger.error("Repaired fragment (NEEDS_REVIEW): %s", repaired)

        # Additional targets (multi-target map)
        for tgt in additional_targets:
            try:
                field_rules.append(
                    assemble_field_rule(
                        table_name=table_name,
                        field_name=field_name,
                        target_table=tgt.table or "",
                        target_field=tgt.field or "",
                        data_type=data_type,
                        validation_function=validation_fn,
                        constraints=constraints,
                        transformations=transformations,
                        relation_keys=make_relation_key(tgt.table, tgt.field),
                    )
                )
            except ValidationError as exc:
                repaired = attempt_repair(
                    {
                        "table_name": table_name,
                        "field_name": field_name,
                        "target_table": tgt.table,
                        "target_field": tgt.field,
                        "data_type": data_type.value if hasattr(data_type, "value") else str(data_type),
                    },
                    str(exc),
                )
                logger.error("Field rule validation failed for %s (additional target): %s", rule.id, exc)
                logger.error("Repaired fragment (NEEDS_REVIEW): %s", repaired)

    return assemble_catalog(field_rules, procedural_rules, validation_description, input_hash)
