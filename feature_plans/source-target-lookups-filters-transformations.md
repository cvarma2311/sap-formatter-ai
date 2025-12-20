# Source/Target-Scoped Lookups, Filters, and Transformations (Design)

This document details the planned implementation for nested lookups, filters, and transformations inside `source` and `target` specs. It extends the core AI-assisted rule compilation framework to support richer enrichment logic per side.

## 1) Scope and Goals
- Add `lookups`, `filters`, and typed `transformations` under `SourceTargetSpec` for both source and target.
- Preserve ordering of lookups/filters/transformations as parsed.
- Support AND/OR chaining for filters and lookup conditions.
- Keep everything deterministic, schema-valid, and cacheable.

## 2) Schema Additions
- **LookupEntry**
  - `rule_type`: CONDITION | EXPECTED | DEFAULT
  - `source_type`: TABLE | CONSTANT | XPATH | CSV_HINT
  - `field`, `cond_value`, `operator`: AND | OR | EQUAL | NOT_EQUAL | IN | NOT_IN | GT | GTE | LT | LTE | NONE
  - `expected_result`
- **FilterEntry**
  - `field`
  - `operator`: EQUAL | NOT_EQUAL | IN | NOT_IN | GT | GTE | LT | LTE | CONTAINS | STARTS_WITH | ENDS_WITH | REGEX
  - `value`
  - `logic`: AND | OR (chaining across filters)
- **TransformationEntry (typed)**
  - `function`: one of String, Math, Probabilistic families (below)
  - `params`: function-specific config (pad_char, pad_length, substring_start/length, concat_fields, numeric operands, probability_threshold, etc.)
- **SourceTargetSpec**
  - Adds: `lookups[]`, `filters[]`, `transformations[]`

## 3) Agents
- **LookupAgent (scoped)**: parse defaults/expected/condition phrases (incl. arrow notation) into ordered lookups; use CSV header hints (`data/agile_payload.csv`) to align fields (`source_type=CSV_HINT` when matched).
- **FilterAgent**: parse filter language (“only when”, “exclude where”, “greater than”, “contains”, “matches regex”) into FilterEntry list with AND/OR logic.
- **TransformationAgent (extended)**: map verbs to typed transformations; request params when implied (e.g., pad char/length); flag NEEDS_REVIEW on unknown.
- Run per side: `source.*` and `target.*` are populated independently.

## 4) Filter Support (examples)
- Operators: EQUAL, NOT_EQUAL, IN/NOT_IN, GT/GTE/LT/LTE, CONTAINS, STARTS_WITH, ENDS_WITH, REGEX.
- Logic: AND/OR chaining in order of appearance.
- Examples:
  - “only when Status = 'ACTIVE'” → EQUAL
  - “exclude where Amount < 0” → LT
  - “where Name contains 'SAP'” → CONTAINS
  - “where Code matches regex ^[A-Z]{3}$” → REGEX

## 5) Transformations Support
- **String**: CONCAT, LEFT_PAD, RIGHT_PAD, UPPER, LOWER, TRIM, SUBSTRING, IS_TEXT, IS_NUMBER.
  - Params: `pad_char`, `pad_length`, `substring_start`, `substring_length`, `concat_fields` (list), etc.
- **Mathematical**: ADD, SUBTRACT, MULTIPLY, DIVIDE (with operands/field refs), ROUND (decimals), COALESCE (first non-null).
- **Probabilistic**:
  - PROBABILITY_THRESHOLD / CONFIDENCE_FILTER (e.g., “apply if p > 0.8”; optional uncertain band `uncertain_low`/`uncertain_high`).
  - TOP_K (e.g., “take top 2 candidates”; params: `k`, optional `tie_handling`, `min_confidence`).
  - SOFTMAX (normalize scores; optional `temperature`).
- Unknown or unsupported verbs → NEEDS_REVIEW with reason.

## 6) Orchestration (LangGraph)
- Add nodes after identity/validation:
  - `build_source_enrichments` → LookupAgent, FilterAgent, TransformationAgent scoped to source.
  - `build_target_enrichments` → same for target.
- Router remains intent-based (field/procedural/lookup); enrichments run for field/lookup paths; procedural may skip or use source filters only.
- Caching: lookup/filter/transform caches keyed by description hash; optional via CLI flags.

## 7) Assembly
- **FieldRuleAssembler**: include `source.lookups/filters/transformations` and `target.lookups/filters/transformations`.
- **ProceduralRuleAssembler**: optionally include filters if used for conditional defaults.
- Do not sort lookups/filters/transformations—preserve emitted order.

## 8) CSV/XPath Alignment
- Helper scans `data/agile_payload.csv` headers for close matches to xpath leaf/arrow segments; if matched, mark `source_type=CSV_HINT` and use that header as the field name. Fallback to TABLE/XPATH when no match.

## 9) Testing
- Lookup tests: defaults/expected with arrow notation; AND/OR operators; CSV hints.
- Filter tests: EQUAL/IN/GT/LT/CONTAINS/REGEX; AND/OR chaining.
- Transformation tests: string (pad/concat/substring/upper/lower), math (add/multiply), probabilistic (threshold).
- Integration: LangGraph run yields populated source/target lookups/filters/transformations in catalog.

## 10) Documentation
- Update README with schema examples for nested lookups/filters/transformations and phrasing guidance.
- Note tracing: `--debug-trace`/LangSmith captures lookup/filter/transform nodes.
