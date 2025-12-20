# AI-Assisted Rule Compilation Framework

Compile human-authored SAP mapping rules (YAML/XLS-derived) into a deterministic JSON rule catalog. The pipeline uses LangGraph for orchestration and heuristics (LLM hooks are stubbed) to classify intents, normalize fields, and emit both field rules and procedural rules.

## What it does (end-to-end flow)
- **Load & validate YAML**: `rule_loader.py` ingests mapping rules (`data/agile_mdg_rules.yaml`), validates into `MappingRule`, and hashes the input for metadata.
- **Intent classification**: `agents/intent_classifier.py` heuristically classifies each rule (simple field, multi-target, procedural, lookup).
- **Identity & relation**: `identity_agent.py` derives `table_name`/`field_name` from xpath/targets; `relation_agent.py` builds canonical relation keys.
- **Data typing & constraints**: `validation_agent.py` normalizes types, detects validation functions, and extracts constraints (required/length/severity/allowed values/pattern/range).
- **Transformations**: `transformation_agent.py` maps phrases to enumerated transformations (not_null/trim/upper/pad_left/substring) with review notices for unknowns.
- **Multi-target mapping**: `multitarget_agent.py` detects “Additionally map …” phrases and emits extra targets.
- **Procedural IR**: `procedural_ir_agent.py` extracts defaults, chunking (size/ordinal), row expansion (delimiter/target), conditions, and ordered steps. Variants include `TEXT_DEFAULTS_AND_CHUNKING`, `TEXT_CHUNKING`, `DEFAULTING_ONLY`, `CONDITIONAL_DEFAULTS`, `ROW_EXPANSION`, `GENERIC_PROCEDURAL`.
- **Lookup/Default rules**: `lookup_agent.py` parses lookup/default/expected patterns into ordered `lookups[]` entries, with CSV header hints (from `data/agile_payload.csv`) to align field names.
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
- `src/orchestration/rule_graph.py` – LangGraph-based DAG orchestration with caching hooks.
- `src/main.py` – CLI entrypoint.
- `data/` – Sample mapping and payload artifacts (`agile_mdg_rules.yaml`, `Agile_payload.xml`, `agile_payload.csv`, `Agile_MDG_Mapping.xlsx`).

## Core behaviors
- **Field rules**: `unique_id = {table}.{field}`, relation keys `{target.structure}.{target.field}`, deterministic ordering by table/field/id.
- **Procedural rules**: support defaults, text chunking with ordinal sequencing, conditional defaults, row expansion (with delimiter), and generic procedural fallback; steps are explicitly ordered (e.g., `apply_defaults`, `chunk_text`, `add_ordinal_sequence`, `row_expansion`, `split_by_delimiter`).
- **Lookups**: ordered `lookups[]` entries with enums for rule_type/operator/source_type; defaults/expected values derived from descriptions, optionally hinted by CSV headers (e.g., `data/agile_payload.csv`).
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

# Enable LangGraph debug tracing (writes alongside outputs)
poetry run python -m src.main --debug-trace

# Enable LangSmith tracing (requires account & API key)
export LANGCHAIN_API_KEY="your-langsmith-key"
export LANGCHAIN_TRACING_V2=true
# optional project name
export LANGCHAIN_PROJECT="sap-rule-compiler"
poetry run python -m src.main --rules data/agile_mdg_rules.yaml
# Alternatively, place these in a local .env (auto-loaded) and run the same command.

# Run tests
poetry run pytest
```

## How to
- **Compile all rules**: `poetry run python -m src.main --rules data/agile_mdg_rules.yaml --out rules/compiled/compiled_rules.json`
- **Compile a specific rule**: `poetry run python -m src.main --rules data/agile_mdg_rules.yaml --id M-001 --out rules/compiled/compiled_rules.json`
  - Outputs: `rules/compiled/M-001-compile.json`, `.pretty.json`, `rule_index.json`, `compile_log.json`
- **Enable LangGraph traces**: add `--debug-trace` to any run
  - Example: `poetry run python -m src.main --rules data/agile_mdg_rules.yaml --debug-trace --out rules/compiled/compiled_rules.json`
  - Outputs an additional `rules/compiled/compiled_rules.debug.json` (or `{ruleid}-compile.debug.json` for per-rule runs)
- **Disable/relocate caches**: `--no-cache` or `--cache-dir .cache_custom`
- **Run tests**: `poetry run pytest`
- **Lookup/default rules**: descriptions like `Default Quantity as 'EA' (Product->QuantityCharacteristic->Quantity)` or “Map the attribute value in unitCode” are parsed into `lookups[]` with ordered defaults/expected values; CSV headers (e.g., `data/agile_payload.csv`) are used to hint matching fields.

## LangGraph orchestration
- The DAG in `src/orchestration/rule_graph.py` runs nodes in sequence: `classify_intent -> identity -> validation -> transformations -> route -> (procedural | field) -> END`.
- To trace execution, wrap the compiled app:
  ```python
  from src.orchestration.rule_graph import _build_graph
  graph = _build_graph(intent_cache=None, transform_cache=None)
  app = graph.compile()
  # Enable debug tracing
  result = app.invoke(state, debug=True)
  print(result.get("__debug__"))
  ```
  (For CLI runs, you can set `DEBUG=1` and add logging to nodes as needed.)
- CLI flag `--debug-trace` enables LangGraph debug traces and writes `<out>.debug.json` next to the compiled outputs.
- To instrument further, add logging inside the node functions in `rule_graph.py` or wrap `app.invoke` with your own tracing hooks.

## How to read traces
- The `*.debug.json` file contains per-rule LangGraph debug data with node execution order, inputs, and outputs.
- For each rule, trace entries typically include:
  - `node`: DAG node name (e.g., `classify_intent`, `identity`, `validation`, `transformations`, `build_field`, `build_procedural`)
  - `input` / `output`: serialized state fragments before/after the node
  - `time` / `duration`: timing metadata if provided by the LangGraph version
- There’s no bundled UI here; options to visualize:
  - Load the debug JSON in a notebook or small HTML/JS timeline to inspect node transitions.
  - Add structured logging in `rule_graph.py` nodes for real-time CLI visibility.
  - Integrate with an external tracer (e.g., LangSmith) by configuring its client around the graph compile/invoke calls if you want a UI-based view.

## LangSmith integration
- Requires a LangSmith account/API key (free tier/trial available; check LangSmith pricing).
- Set environment variables before running:
  ```bash
  export LANGCHAIN_API_KEY="your-langsmith-key"
  export LANGCHAIN_TRACING_V2=true
  export LANGCHAIN_PROJECT="sap-rule-compiler"  # optional
  poetry run python -m src.main --rules data/agile_mdg_rules.yaml
  ```
- With these set, LangGraph will emit traces to LangSmith; inspect them in the LangSmith UI under your project. No code changes needed beyond env vars (langsmith dependency is included).
- You can also place these in a local `.env` (auto-loaded). To verify they’re picked up:
  ```bash
  poetry run python - <<'PY'
  import os
  from src.utils.env import load_env_file
  load_env_file()
  print("Has API key:", bool(os.getenv("LANGCHAIN_API_KEY")))
  print("Tracing v2:", os.getenv("LANGCHAIN_TRACING_V2"))
  print("Project:", os.getenv("LANGCHAIN_PROJECT"))
  print("Endpoint:", os.getenv("LANGCHAIN_ENDPOINT"))
  PY
  ```
- If you see `Has API key: False`, update `.env` at repo root with:
  ```
  LANGCHAIN_API_KEY=your-key
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_PROJECT=sap-rule-compiler        # optional
  LANGCHAIN_ENDPOINT=https://api.smith.langchain.com   # or https://eu.api.smith.langchain.com for EU
  ```
- 403/Forbidden from LangSmith usually means invalid/expired key or wrong region endpoint. Regenerate the key and/or set `LANGCHAIN_ENDPOINT` for your region, then rerun the CLI.

## Outputs
- `compiled_rules.json` – Minified catalog.
- `compiled_rules.pretty.json` – Human-readable catalog.
- `rule_index.json` – Quick lookup for `unique_id -> {table, field, relation_keys}`.
- `compile_log.json` – Counts and output metadata.

## Notes and next steps
- LLM integration is stubbed; heuristics drive all decisions for now. `utils/llm_client.py` is ready for injection when networked models are available.
- Caching uses local JSON files under `.cache/` for intents and transformations (override with `--cache-dir` or disable via `--no-cache`).
- Extend agents to cover richer lookup rules, strengthen repair logic, and broaden procedural patterns as needed.
