# AI-Assisted Rule Compilation Framework

Compile human-authored SAP mapping rules (YAML/XLS-derived) into a deterministic JSON rule catalog. The pipeline uses heuristics (LLM hooks are stubbed) to classify intents, normalize fields, and emit both field rules and procedural rules.

## What it does
- Loads mapping rules from YAML (default: `data/agile_mdg_rules.yaml`).
- Classifies intent (simple, multi-target, procedural, lookup heuristic).
- Normalizes table/field identities, data types, relation keys, and transformations.
- Emits `field_rules` for direct mappings and `procedural_rules` for defaults/chunking cases.
- Writes deterministic JSON outputs plus a lightweight index and compile log.

## Project layout
- `src/data_models.py` – Pydantic models and enums for mapping, catalog, intents, and transformations.
- `src/rule_loader.py` – YAML ingestion, validation, and deterministic input hashing.
- `src/normalization/` – Type, ID, transformation, and relation normalizers.
- `src/agents/` – Heuristic agents: intent, identity, relation, validation, transformations, multi-target, procedural IR, repair stubs.
- `src/assembler/` – Builders for field rules, procedural rules, and final catalog.
- `src/orchestration/rule_graph.py` – End-to-end compilation pipeline with caching hooks.
- `src/main.py` – CLI entrypoint.
- `data/` – Sample mapping and payload artifacts (`agile_mdg_rules.yaml`, `Agile_payload.xml`, `agile_payload.csv`, `Agile_MDG_Mapping.xlsx`).

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
```

## Outputs
- `compiled_rules.json` – Minified catalog.
- `compiled_rules.pretty.json` – Human-readable catalog.
- `rule_index.json` – Quick lookup for `unique_id -> {table, field, relation_keys}`.
- `compile_log.json` – Counts and output metadata.

## Notes and next steps
- LLM integration is stubbed; heuristics drive all decisions for now. `utils/llm_client.py` is ready for injection when networked models are available.
- Caching uses local JSON files under `.cache/` for intents and transformations.
- Extend agents to cover richer lookup rules and add schema repair logic in `repair_agent.py` for stricter validation.
