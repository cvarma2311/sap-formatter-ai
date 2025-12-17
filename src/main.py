import argparse
import json
import os
from pathlib import Path

from src.orchestration.rule_graph import compile_rules_with_cache
from src.rule_loader import load_rules
from src.utils.env import load_env_file
from src.utils.logging import get_logger

logger = get_logger(__name__)


def write_outputs(catalog, out_path: Path) -> None:
    parent = out_path.parent
    if parent.exists() and not parent.is_dir():
        raise ValueError(f"Output parent path exists and is not a directory: {parent}")
    parent.mkdir(parents=True, exist_ok=True)

    payload = catalog.model_dump(mode="json")
    with out_path.open("w") as f:
        json.dump(payload, f, separators=(",", ":"))

    pretty_path = out_path.with_suffix(".pretty.json")
    with pretty_path.open("w") as f:
        json.dump(payload, f, indent=2)

    # Build a lightweight index for quick lookup
    index = {
        rule.unique_id: {
            "table": rule.table_name,
            "field": rule.field_name,
            "relation_keys": rule.relation_keys,
        }
        for rule in catalog.field_rules
    }
    with out_path.with_name("rule_index.json").open("w") as f:
        json.dump(index, f, indent=2)

    compile_log = {
        "field_rule_count": len(catalog.field_rules),
        "procedural_rule_count": len(catalog.procedural_rules),
        "output": str(out_path),
    }
    with out_path.with_name("compile_log.json").open("w") as f:
        json.dump(compile_log, f, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-assisted rule compilation framework")
    parser.add_argument("--rules", default="data/agile_mdg_rules.yaml", help="Path to YAML rules file")
    parser.add_argument("--validation-description", default=None, help="Validation description for catalog metadata")
    parser.add_argument("--out", default="rules/compiled/compiled_rules.json", help="Path to compiled JSON output")
    parser.add_argument("--id", dest="rule_id", default=None, help="Optional rule id filter")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI-dependent steps (heuristics only)")
    parser.add_argument("--cache-dir", default=".cache", help="Directory for caches (intent/transformation).")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching for debugging.")
    parser.add_argument("--debug-trace", action="store_true", help="Enable LangGraph debug tracing and emit .debug.json")
    return parser.parse_args()


def main() -> None:
    load_env_file()
    args = parse_args()
    if args.skip_ai:
        logger.info("skip-ai enabled: running heuristics-only pipeline.")
    if os.environ.get("LANGCHAIN_TRACING_V2"):
        logger.info("LangSmith tracing enabled via LANGCHAIN_TRACING_V2.")

    rules_path = Path(args.rules)
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

    rules, input_hash = load_rules(rules_path, rule_id=args.rule_id)
    if not rules:
        logger.warning("No rules loaded; exiting.")
        return

    out_path = Path(args.out)
    if args.rule_id:
        # Ensure per-rule outputs are named {ruleid}-compile.json inside the provided directory.
        suffix = out_path.suffix or ".json"
        parent = out_path.parent if out_path.suffix else out_path
        out_path = parent / f"{args.rule_id}-compile{suffix}"

    cache_dir = None if args.no_cache else Path(args.cache_dir)

    catalog, debug_traces = compile_rules_with_cache(
        rules,
        args.validation_description,
        input_hash,
        cache_dir=cache_dir,
        use_cache=not args.no_cache,
        debug=args.debug_trace,
    )
    write_outputs(catalog, out_path)
    if args.debug_trace and debug_traces:
        debug_path = out_path.with_suffix(".debug.json")
        with debug_path.open("w") as f:
            json.dump(debug_traces, f, indent=2)
    logger.info("Compilation complete. Field rules: %s, procedural rules: %s", len(catalog.field_rules), len(catalog.procedural_rules))


if __name__ == "__main__":
    main()
