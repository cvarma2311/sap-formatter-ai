import argparse
import os
import pandas as pd
from rule_loader import RuleLoader
from ai_interpreter import RuleInterpreter
from validator import Validator
from report_generator import ReportGenerator
from data_models import ExecutableRule

def main():
    """Main orchestration script for the AI-Powered Validation Framework."""
    parser = argparse.ArgumentParser(description="AI-Powered XML/CSV Validation Framework.")
    parser.add_argument("--rules", type=str, help="Path to the YAML rules file.", default="data/agile_mdg_rules.yaml")
    parser.add_argument("--input-csv", type=str, default="data/agile_payload.csv", help="Path to the pre-flattened CSV file to validate.")
    parser.add_argument("--id", type=str, default=None, help="Run validation for a single rule ID from the YAML file.")
    parser.add_argument("--output-dir", type=str, default="reports", help="Directory to save reports.")
    parser.add_argument("--skip-ai", action='store_true', help="Skip the AI interpretation step and run only static checks.")
    
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    print("--- Starting Validation Process ---")
    
    # 1. Load rules from YAML
    try:
        loader = RuleLoader()
        all_rules = loader.load_from_yaml(args.rules)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading rules: {e}")
        return

    # Filter for a single rule if an ID is provided
    if args.id:
        print(f"--- Filtering for single rule ID: {args.id} ---")
        rules_to_process = [r for r in all_rules if r.id == args.id]
        if not rules_to_process:
            print(f"Error: Rule ID '{args.id}' not found in {args.rules}.")
            return
    else:
        rules_to_process = all_rules

    # 2. Load the pre-flattened CSV data
    df = pd.DataFrame()
    try:
        print(f"--- Loading data from CSV: {args.input_csv} ---")
        df = pd.read_csv(args.input_csv)
        print(f"Successfully loaded CSV with shape {df.shape}.")
    except FileNotFoundError:
        print(f"Error: Input CSV file '{args.input_csv}' not found.")
        return
    except Exception as e:
        print(f"Error loading input CSV: {e}")
        return
    
    # 3. Interpret rules with AI (optional)
    executable_rules = []
    if not args.skip_ai:
        api_key = ""
        if not api_key:
            print("Warning: OPENAI_API_KEY not set. Skipping AI interpretation. To run AI rules, set the environment variable.")
        else:
            interpreter = RuleInterpreter(api_key=api_key, raw_df=df)
            for rule in rules_to_process:
                if rule.description: # Only interpret if a description exists
                    executable_rules.extend(interpreter.interpret_rule(rule))
    else:
        print("Skipping AI rule interpretation as requested.")
        
    # If an ID was specified, print the AI's interpretation plan
    if args.id and executable_rules:
        print(f"\n--- AI-Generated Validation Plan for Rule '{args.id}' ---")
        for i, exec_rule in enumerate(executable_rules):
            print(f"Step {i+1}:")
            print(exec_rule.model_dump_json(indent=2))
        print("----------------------------------------------------\n")

    # Always add static rules (required, length, etc.) for the rules being processed
    for rule in rules_to_process:
        if rule.source_field: # Only add static checks if a source field is defined
            base_rule_props = {'id': rule.id, 'severity': rule.severity, 'source_column': rule.source_field}
            if rule.required:
                executable_rules.append(ExecutableRule(type='REQUIRED_CHECK', **base_rule_props))
            if rule.max_length > 0:
                executable_rules.append(ExecutableRule(type='LENGTH_CHECK', expected_value=str(rule.max_length), **base_rule_props))

    # 4. Validate Data
    validator = Validator(df)
    results = validator.execute(executable_rules)

    # 5. Generate reports
    report_suffix = f"_{args.id}" if args.id else ""
    report_generator = ReportGenerator(results)
    report_generator.generate_html(
        "templates/report_template.html", 
        os.path.join(args.output_dir, f"validation_report{report_suffix}.html")
    )
    report_generator.generate_csv(os.path.join(args.output_dir, f"validation_report{report_suffix}.csv"))
    report_generator.generate_excel(os.path.join(args.output_dir, f"validation_report{report_suffix}.xlsx"))
    
    print(f"--- Validation Process Finished ---")
    print(f"Found {len(results)} total validation failures.")
    print(f"Reports generated in '{args.output_dir}' directory.")

if __name__ == "__main__":
    main()
