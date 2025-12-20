# AI-Assisted Rule Compilation Framework (Rule-Only)

## 1) Business Objective and Business Logic

### 1.1 What the system does (business terms)
Your SAP integration teams typically have:
- Source documents (XML exports or XML-derived CSV extracts)
- Target structures (SAP staging tables like MARA_SRC, T134, etc.)
- Human-authored mapping rules (YAML / XLS) containing:
  - field names
  - xpath
  - data types
  - required/length/severity
  - natural language transformation & mapping logic

**Goal:** Convert this human-authored mapping spec into a standardized, enterprise-grade rule catalog JSON, which downstream systems can:
- use to generate validators (later)
- generate transformation pipelines (later)
- generate documentation
- generate test data
- produce governance-ready mapping traceability

### 1.2 Why single prompt fails (business logic reason)
Descriptions encode different intent classes:
- “As-Is” → field equality mapping
- “Default values if not blank” → conditional defaulting
- “Split 72 chars and increment ordinal” → chunking + row-expansion
- “Map to additional field” → multi-target mapping dependency

So your compiler must behave like a mapping compiler, not like a “text-to-json generator”.

### 1.3 The key business rules the compiler must enforce
These rules make the compiled JSON consistent and safe:
- **BR-01: Intent Classification is mandatory**  
  Every YAML rule must be classified into an enum `RuleIntent`. Downstream pipeline is chosen strictly from intent.
- **BR-02: One YAML entry may compile into multiple JSON rules**  
  Example: “Additionally map to ReceiverProductInternalID” produces 2 `field_rules`: `ProductInternalID → MATNR` and `ProductInternalID → ReceiverProductInternalID`.
- **BR-03: Procedural mapping is not expressed as key equality**  
  Procedural descriptions must compile into `procedural_rules[]` not `field_rules[]`.
- **BR-04: Transformation lists must be enums**  
  No free text transformations. Every item must be from the enum vocabulary.
- **BR-05: All compiled rules must be schema-valid**  
  If schema invalid: attempt repair; otherwise mark `NEEDS_REVIEW` and persist with error detail.
- **BR-06: Output JSON must be deterministic**  
  Given same YAML + same schema version: rule IDs, ordering, and normalization must be reproducible.

---

## 2) Data Contracts and Schemas (Pydantic + Enums)

### 2.1 “Source language” schema (YAML → MappingRule)
Your YAML is compiled into this model:

`MappingRule`
- id (string)
- name (string)
- source_field (string)
- xpath (string)
- type (enum-ish from mapping doc: CHAR/NUM/DATE…)
- required (bool)
- max_length (int? optional)
- severity (E/W/I)
- description (string)
- target.structure (string)
- target.field (string)

### 2.2 “Target language” schema (compiled JSON)
Your desired `field_rules` schema plus a procedural schema.

**Catalog**
- validation_description
- field_rules[]
- procedural_rules[]
- metadata (schema_version, generated_at, compiler_version, input_hash…)

**FieldRule**
- unique_id (string)
- table_name (enum-ish if you have known tables; else string)
- field_name (string)
- relation_keys (string “STRUCT.FIELD”)
- data_type (enum)
- config.key_config.validation_function (enum)
- config.key_config.source spec
- config.key_config.target spec

**SourceTargetSpec**
- table
- field
- transformations[] (enum list)

**ProceduralRule**
- rule_type (enum: DEFAULTING, TEXT_CHUNKING, MULTI_TARGET_MAP, etc.)
- condition (enum: NOT_BLANK, IS_BLANK, ALWAYS)
- source spec
- targets[] (fields to populate)
- steps[] (structured steps: default, chunk, ordinal)

Key point: LLM should not write `FieldRule` directly for complex rules; it should write IR that code normalizes.

---

## 3) Project Structure (expanded with business modules)
```
src/
├── main.py
├── rule_loader.py
├── data_models.py                # all enums + pydantic models
├── normalization/
│   ├── type_normalizer.py        # CHAR -> string, etc.
│   ├── id_normalizer.py          # unique_id conventions, deterministic ordering
│   ├── transformation_normalizer.py
│   └── relation_normalizer.py
├── orchestration/
│   ├── rule_graph.py             # LangGraph DAG
│   └── state.py                  # RuleCompileState
├── agents/
│   ├── intent_classifier.py
│   ├── extractor_agents.py       # shared utilities for parsing description
│   ├── identity_agent.py
│   ├── relation_agent.py
│   ├── validation_agent.py
│   ├── transformation_agent.py
│   ├── multitarget_agent.py      # “Additionally map to …”
│   ├── procedural_ir_agent.py
│   ├── defaulting_agent.py
│   ├── chunking_agent.py
│   └── repair_agent.py
├── assembler/
│   ├── field_rule_assembler.py
│   ├── procedural_rule_assembler.py
│   └── catalog_assembler.py
├── utils/
│   ├── llm_client.py
│   ├── cache.py
│   ├── hashing.py
│   └── logging.py
```

---

## 4) Multi-Agent Orchestration (LangGraph) – Detailed

### 4.1 State Design (what flows between agents)
`RuleCompileState`
- mapping_rule (the YAML entry)
- intent (enum)
- sub_intents (list) — important for “Additionally map…”
- identity_part
- relation_part
- validation_part
- transform_part
- procedural_ir
- compiled_rules[] (because one YAML can emit multiple)
- errors[]

### 4.2 DAG Routing Rules (business logic)
Router decides pipeline:
- If description contains “Default … when …” OR “Increment ordinal” OR “72 characters” → `PROCEDURAL_MAPPING`
- If description contains “Additionally map to …” → `MULTI_TARGET_MAP` (emits extra `FieldRule`)
- If description contains “Lookup / T134 / MTART allowed values” → `LOOKUP_RULE`
- Else → `SIMPLE_FIELD_RULE`

The router should use LLM classification + heuristics. Heuristics reduce cost and increase determinism.

---

## 5) Agent Responsibilities + Implementation Details

### 5.1 IntentClassifierAgent (Gate)
**Business logic**
- classifies intent using description keywords + YAML fields
- returns enum + confidence + rationale

**Implementation**
- Use OpenAI structured output with a schema like: intent enum, confidence float 0..1, evidence snippets (short)
- Cache key: `hash(description + target + xpath)`

### 5.2 MultiTargetAgent (handles “Additionally map to …”)
**Business logic**
- Detects additional mapping targets embedded in description
- Example: “Additionally map the field value to ReceiverProductInternalID” means two outputs: main mapping (`ProductInternalID → MATNR`) and extra mapping (`ProductInternalID → ReceiverProductInternalID`)

**Implementation**
- Extract target table/field from pattern (Product->ReceiverProductInternalID)
- if not explicit: infer from phrase

Output IR
```json
{
  "primary_target": {"structure": "MARA_SRC", "field": "MATNR"},
  "additional_targets": [{"table": "Product", "field": "ReceiverProductInternalID"}]
}
```
Then pipeline repeats FieldRule build for each target.

### 5.3 IdentityAgent
**Business logic**
- Determine canonical table_name from xpath: `//Product/... → Product`
- If xpath deeper: still anchor on first segment
- Determine field_name: prefer YAML xpath leaf node; fallback to YAML source_field

**Implementation details**
- Use deterministic parsing first; only call LLM if ambiguous.

### 5.4 RelationAgent
**Business logic**
- Canonical relation_keys = `{target.structure}.{target.field}`

**Implementation**
- Pure code (no LLM) unless you want relationship keys beyond that.

### 5.5 ValidationAgent (rule-building only)
**Business logic**
- Select validation_function enum:
  - “As-Is” → equal
  - “must be one of” → in
  - “pattern” / “format” → regex
  - “between” → range
- Select data_type enum:
  - YAML type: CHAR → string
  - NUMC, DEC, etc. mapping table

**Implementation**
- Use deterministic mapping table first
- LLM only when YAML type is missing or unclear

### 5.6 TransformationAgent
**Business logic**
- Convert phrases into enumerated transformations:
  - “not blank” / “required” → not_null
  - “trim” → trim
  - “uppercase” → upper
  - “pad to 4” → pad_left:4
  - “first 72 characters” → substring:0:72

**Implementation**
- Two-step:
  - heuristic extractor (regex for pad/substring)
  - LLM resolver for edge language
- Strict validation:
  - transformations must match enum patterns
  - if unknown: emit NEEDS_REVIEW entry with reason

### 5.7 ProceduralIRAgent (for MBD-001)
**Business logic**
- Extract:
  - condition: “when X not blank”
  - defaults: fixed assignments
  - chunking: split size, ordinal rule, mapping target
  - sequence order (defaults first, then chunk)

**Implementation**
LLM produces a strongly typed IR:
```json
{
  "condition": {"type": "NOT_BLANK", "field": "MATERIAL_BASIC_TEXT"},
  "defaults": [...],
  "chunking": {"chunk_size": 72, "ordinal_start": 1, "ordinal_increment": 1, "map_to": "SAPScriptLineText"}
}
```

### 5.8 DefaultingAgent + ChunkingAgent (IR refinement)
These agents are not necessarily LLM — they can be code normalizers.

**DefaultingAgent**
- Validates defaults are explicit
- Normalizes field names and constant types

**ChunkingAgent**
- Normalizes substring/ordinal details
- Ensures chunk size numeric and positive

### 5.9 RepairAgent (schema rescue)
**Business logic**
- If any fragment fails Pydantic validation:
  - attempt one “repair” call with the invalid fragment, allowed enums, exact error message from Pydantic
  - If still invalid: store partial output with NEEDS_REVIEW

---

## 6) Deterministic Assemblers (No LLM)

### 6.1 FieldRuleAssembler
- Merges pieces into your target format:
  - `unique_id = {table_name}.{field_name}`
  - `relation_keys = {target.structure}.{target.field}`
  - `config.key_config`: validation_function, source spec, target spec

### 6.2 ProceduralRuleAssembler
- Builds `procedural_rules[]` from IR:
  - Example output type: `TEXT_DEFAULTS_AND_CHUNKING`
  - Includes: condition, defaults list, chunking spec, target structure & fields

### 6.3 CatalogAssembler
- Builds final JSON:
  - stable ordering by: source table, field_name, rule_id
- Adds metadata:
  - input YAML hash
  - schema version
  - compiler version
  - generated timestamp

---

## 7) Detailed Rule Normalization Rules (Business-Driven)

### 7.1 Naming conventions
- `unique_id` always `Table.Field`
- `relation_keys` always `STRUCT.FIELD`

### 7.2 Type mapping table
A deterministic map:
- CHAR, STRING → string
- NUMC, INT → integer
- DEC, CURR → decimal
- DATE, DATS → date

### 7.3 Required/Severity propagation
Even though your schema example doesn’t show required/max_length/severity, you likely want them. If you want, we add:
```json
"constraints": {
  "required": true,
  "max_length": 18,
  "severity": "E"
}
```
This is still rule-only, but preserves business meaning.

---

## 8) Caching Strategy (Cost + Consistency)
Cache at the subset level:
- intent cache (description hash)
- transformation cache (description hash)
- procedural IR cache (description hash)
- multi-target cache (description hash)

Use:
- local JSON cache (dev)
- Redis (prod)

Benefit: repeated phrases like “As-Is” become nearly free.

---

## 9) CLI and Outputs

### 9.1 CLI
```bash
python -m src.main \
  --rules rules/input/mapping.yml \
  --validation-description Agile_to_MDG_Validation \
  --out rules/compiled/compiled_rules.json
```

### 9.2 Output files
- `compiled_rules.json` (minified)
- `compiled_rules.pretty.json` (for humans)
- `rule_index.json` (quick search: rule_id → output rule keys)
- `compile_log.json` (errors, needs_review, caching stats)

---

## 10) Walkthrough: How Your Two Example Rules Compile

### Example A: M-001 (“As-Is + Additionally map to ReceiverProductInternalID”)
Compilation outcome:
- `field_rules[]` contains:
  - `ProductInternalID → MARA_SRC.MATNR`
  - `ProductInternalID → Product.ReceiverProductInternalID` (additional target)

### Example B: MBD-001 (defaults + chunking + ordinal)
Compilation outcome:
- `procedural_rules[]` contains:
  - `rule_type: TEXT_DEFAULTS_AND_CHUNKING`
  - condition: `NOT_BLANK` on `MATERIAL_BASIC_TEXT`
  - defaults: `TextExistsIndicator=X`, `TypeCode=GRUN`, `LanguageCode=en`, `FormatCode=*`
  - chunking: `size=72`, `ordinal start=1`, `increment=1`, `map to SAPScriptLineText`
- No “equal compare rule” is produced because this description is not equality—it’s procedural mapping logic.

---

## 11) Suggested Development Milestones (Practical)
- **Milestone 1:** Enums + Pydantic schemas; YAML RuleLoader; deterministic identity extraction (xpath → table/field)
- **Milestone 2:** Intent classification (LLM + heuristics + caching); simple FieldRule pipeline end-to-end
- **Milestone 3:** MultiTargetAgent + repeatable rule emission; add constraints propagation (required/length/severity)
- **Milestone 4:** Procedural IR pipeline (defaults + chunking); ProceduralRuleAssembler
- **Milestone 5:** RepairAgent + error persistence; Output JSON + pretty + index + logs

## 12) Extension Plan: Source/Target-Scoped Lookups, Filters, and Transformations

### 12.1 Schema extensions (nested under source/target)
- **SourceTargetSpec**: add nested arrays:
  - `lookups[]` (conditions/expected/default entries scoped to source or target)
  - `filters[]` (field/value/operator predicates applied before/after transforms)
  - `transformations[]` (extend current list with typed configs: string/math/probabilistic)
- **LookupEntry (scoped)**:
  - `rule_type` enum: CONDITION, EXPECTED, DEFAULT
  - `source_type` enum: TABLE, CONSTANT, XPATH, CSV_HINT
  - `field`, `cond_value`, `operator` enum (AND, OR, EQUAL, NOT_EQUAL, IN, NOT_IN, GT, GTE, LT, LTE, NONE), `expected_result`
- **FilterEntry**:
  - `field`, `operator` (EQUAL, NOT_EQUAL, IN, NOT_IN, GT, GTE, LT, LTE, CONTAINS, STARTS_WITH, ENDS_WITH), `value`, `logic` (AND/OR chaining)
- **TransformationEntry (typed)**:
  - `function` enum (CONCAT, LEFT_PAD, RIGHT_PAD, UPPER, LOWER, TRIM, IS_TEXT, IS_NUMBER, SUBSTRING, ADD, SUBTRACT, MULTIPLY, DIVIDE, PROBABILITY_THRESHOLD)
  - `params` object (e.g., pad_char, pad_length, substring_start/length, concat_fields, numeric operands, probability_threshold)

### 12.2 Agents (modular, per concern)
- **LookupAgent (scoped)**: parse description into ordered lookups; infer table/field from xpath/arrow notation; use CSV header hints (data/agile_payload.csv) for source/target field alignment; enforce enums.
- **FilterAgent**: parse filter phrasing (“only when <field> = <value>”, “exclude where…”, “greater than…”) into FilterEntry list with logic chaining.
- **TransformationAgent (extended)**: map string/math/probabilistic verbs to typed TransformationEntry; prompt for pad char/length if implied; mark NEEDS_REVIEW on unknown.
- Run per side: attach outputs to `source.lookups/filters/transformations` and `target.lookups/filters/transformations`.

### 12.3 Orchestration updates (LangGraph)
- Add branches after identity/validation:
  - `build_source_enrichments` → LookupAgent/FilterAgent/TransformationAgent for source.
  - `build_target_enrichments` → same for target.
- Router stays intent-based (field/procedural/lookup); enrichments run for field and lookup paths; procedural may skip or use source filters.
- Caching: add lookup/filter/transform caches keyed by description hash; still optional via CLI flags.

### 12.4 Assembly updates
- **FieldRuleAssembler**: include source/target `lookups`, `filters`, `transformations` in `SourceTargetSpec`.
- **ProceduralRuleAssembler**: optionally accept source/target filters if needed for conditional defaults.
- Preserve ordering from agents; do not resort lookups/filters/transformations.

### 12.5 CSV/XPath alignment
- Helper scans `data/agile_payload.csv` headers for close matches to xpath leafs/arrow segments; annotate with `source_type=CSV_HINT` when matched.
- Fallback to TABLE/XPATH names when no match.

### 12.6 Testing
- Unit tests per agent:
  - Lookups: defaults/expected with arrow notation; AND/OR operators; CSV hints.
  - Filters: parse EQUAL/IN/GT/LT/CONTAINS patterns; logic chaining.
  - Transformations: pad/concat/substring/upper/lower/math/probability threshold params.
- Integration: LangGraph run on sample rules yielding populated source/target lookups/filters/transforms in catalog.

### 12.7 Documentation
- README: update schema examples showing source/target-scoped lookups/filters/transformations; phrasing guidance; CSV hint usage.
- Trace/debug: `--debug-trace` and LangSmith capture lookup/filter/transform nodes when enabled.
