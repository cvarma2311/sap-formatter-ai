# AI-Assisted Rule Compilation Framework

Compile human-authored SAP mapping rules (YAML/XLS-derived) into a deterministic JSON rule catalog. The pipeline uses heuristics (LLM hooks are stubbed) to classify intents, normalize fields, and emit both field rules and procedural rules.

## What it does (end-to-end flow)
- **Load & validate YAML**: `rule_loader.py` ingests mapping rules (`data/agile_mdg_rules.yaml`), validates into `MappingRule`, and hashes the input for metadata.
- **Intent classification**: `agents/intent_classifier.py` heuristically classifies each rule (simple field, multi-target, procedural, lookup).
- **Identity & relation**: `identity_agent.py` derives `table_name`/`field_name` from xpath/targets; `relation_agent.py` builds canonical relation keys.
- **Data typing & constraints**: `validation_agent.py` normalizes types, detects validation functions, and extracts constraints (required/length/severity/allowed values/pattern/range).
- **Transformations**: `transformation_agent.py` maps phrases to enumerated transformations (not_null/trim/upper/pad_left/substring) with review notices for unknowns.
- **Multi-target mapping**: `multitarget_agent.py` detects “Additionally map …” phrases and emits extra targets.
- **Procedural IR**: `procedural_ir_agent.py` extracts defaults, chunking (size/ordinal), row expansion (delimiter/target), conditions, and ordered steps. Variants include `TEXT_DEFAULTS_AND_CHUNKING`, `TEXT_CHUNKING`, `DEFAULTING_ONLY`, `CONDITIONAL_DEFAULTS`, `ROW_EXPANSION`, `GENERIC_PROCEDURAL`.
- **Normalization**: `normalization/` enforces deterministic type mapping, IDs, relation keys, and transformation enums.
- **Repair hook**: `repair_agent.py` attempts light enum normalization and annotates NEEDS_REVIEW fragments on validation failures.
- **Assembly**: `assembler/` builds `FieldRule`, `ProceduralRule`, and the final `Catalog` with deterministic ordering and metadata (schema_version, generated_at, compiler_version, input_hash).
- **Outputs**: JSON catalog (minified + pretty), rule index, and compile log.

## Project layout
- `src/data_models.py` – Pydantic models and enums for mapping, catalog, intents, and transformations.
- `src/rule_loader.py` – YAML ingestion, validation, and deterministic input hashing.
- `src/normalization/` – Type, ID, transformation, and relation normalizers.
- `src/agents/` – Heuristic agents: intent, identity, relation, validation, transformations, multi-target, procedural IR, repair stubs.
- `src/assembler/` – Builders for field rules, procedural rules, and final catalog.
- `src/orchestration/rule_graph.py` – End-to-end compilation pipeline with caching hooks.
- `src/main.py` – CLI entrypoint.
- `data/` – Sample mapping and payload artifacts (`agile_mdg_rules.yaml`, `Agile_payload.xml`, `agile_payload.csv`, `Agile_MDG_Mapping.xlsx`).

## Core behaviors
- **Field rules**: `unique_id = {table}.{field}`, relation keys `{target.structure}.{target.field}`, deterministic ordering by table/field/id.
- **Procedural rules**: support defaults, text chunking with ordinal sequencing, conditional defaults, row expansion (with delimiter), and generic procedural fallback; steps are explicitly ordered (e.g., `apply_defaults`, `chunk_text`, `add_ordinal_sequence`, `row_expansion`, `split_by_delimiter`).
- **Constraints**: propagate required, max_length, severity, allowed_values, regex pattern, and numeric range when present.
- **Transformations**: only enumerated values emitted; unknown phrases are flagged via compile warnings.
- **Caching**: intent and transformation results cached to JSON (optional); disable via `--no-cache` or relocate via `--cache-dir`.

## Quickstart
```bash
# Install deps (Poetry recommended)
poetry install

# Compile all rules using sample YAML
poetry run python -m src.main \
  --rules data/agile_mdg_rules.yaml \
  --validation-description Agile_to_MDG_Validation \
  --out rules/compiled/compiled_rules.json

# Compile a single rule by id (for debugging)
poetry run python -m src.main --id M-001
# Outputs will be named rules/compiled/M-001-compile.json (plus pretty/index/log)

# Disable caches or change cache location
poetry run python -m src.main --no-cache
poetry run python -m src.main --cache-dir .cache_custom

# Run tests
poetry run pytest
```

## Outputs
- `compiled_rules.json` – Minified catalog.
- `compiled_rules.pretty.json` – Human-readable catalog.
- `rule_index.json` – Quick lookup for `unique_id -> {table, field, relation_keys}`.
- `compile_log.json` – Counts and output metadata.

## Notes and next steps
- LLM integration is stubbed; heuristics drive all decisions for now. `utils/llm_client.py` is ready for injection when networked models are available.
- Caching uses local JSON files under `.cache/` for intents and transformations (override with `--cache-dir` or disable via `--no-cache`).
- Extend agents to cover richer lookup rules, strengthen repair logic, and broaden procedural patterns as needed.
