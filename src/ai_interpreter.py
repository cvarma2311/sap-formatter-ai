import json
import re
from typing import Any, Dict, List, Optional, Set

import openai
import pandas as pd

from data_models import ExecutableRule, MappingRule

class RuleInterpreter:
    """
    Uses an AI model to convert natural language rule descriptions
    into machine-readable ExecutableRule objects.
    """

    def __init__(self, api_key: str, model: str = "gpt-4-turbo", raw_df: Optional[pd.DataFrame] = None, tag_value_samples: Optional[Dict[str, List[str]]] = None):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self._cache = {}
        # Cache a small map of tag -> sample values from the CSV so we can feed them to the AI
        self._tag_value_samples = tag_value_samples or self._build_tag_value_samples(raw_df)
        print(f"AI Rule Interpreter initialized with model {self.model}.")

    def _build_tag_value_samples(self, raw_df: Optional[pd.DataFrame], sample_size: int = 3) -> Dict[str, List[str]]:
        """
        Creates a map of tag -> example values from the provided CSV.
        Keeps the list small to avoid blowing up prompt length.
        """
        if raw_df is None or raw_df.empty or 'tag' not in raw_df or 'value' not in raw_df:
            return {}

        non_empty = raw_df[(raw_df['value'].notna()) & (raw_df['value'] != '')]
        samples: Dict[str, List[str]] = {}

        for tag, group in non_empty.groupby('tag'):
            vals = group['value'].astype(str).head(sample_size).tolist()
            if vals:
                samples[tag] = vals
        return samples

    def _extract_related_tags(self, description: Optional[str]) -> Set[str]:
        """
        Pull potential tag names from the description by matching known CSV tags
        that appear as substrings. Keeps matches loose to catch names like ReceiverProductInternalID.
        """
        if not description or not self._tag_value_samples:
            return set()

        desc_lower = description.lower()
        matches: Set[str] = set()
        for tag in self._tag_value_samples.keys():
            if len(tag) < 3: # avoid spurious tiny matches
                continue
            if tag.lower() in desc_lower:
                matches.add(tag)
        return matches

    def _build_csv_context_for_rule(self, rule: MappingRule, simple_source_field_name: str, max_tags: int = 6) -> Dict[str, List[str]]:
        """
        Collects a limited set of tag -> values to send to the AI for this rule.
        Always tries to include the source tag, plus any tags referenced in the description.
        """
        if not self._tag_value_samples:
            return {}

        candidate_tags: List[str] = []
        if simple_source_field_name and simple_source_field_name in self._tag_value_samples:
            candidate_tags.append(simple_source_field_name)

        related_tags = self._extract_related_tags(rule.description)
        for tag in related_tags:
            if tag not in candidate_tags:
                candidate_tags.append(tag)

        # Limit the number of tags to keep the prompt concise
        limited_tags = candidate_tags[:max_tags]
        return {tag: self._tag_value_samples[tag][:3] for tag in limited_tags if tag in self._tag_value_samples}

    def _get_executable_rule_schema(self) -> Dict[str, Any]:
        """Generates a JSON schema for the ExecutableRule Pydantic model."""
        return ExecutableRule.model_json_schema()

    def interpret_rule(self, rule: MappingRule) -> List[ExecutableRule]:
        """
        Converts a single MappingRule into a list of ExecutableRules using AI.
        Caches results based on the rule's description to avoid redundant API calls.
        """
        cache_key = rule.model_dump_json() # Cache based on the full rule content
        if cache_key in self._cache:
            print(f"Cache hit for rule '{rule.id}'.")
            return self._cache[cache_key]

        print(f"Interpreting rule '{rule.id}' via AI: {rule.description[:70]}...")

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_validation_rules",
                    "description": "Creates a set of machine-readable validation rules from a natural language description.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rules": {
                                "type": "array",
                                "items": self._get_executable_rule_schema(),
                            }
                        },
                        "required": ["rules"],
                    },
                },
            }
        ]

        # Extract the simple field name from the XPath for clarity in the prompt
        simple_source_field_name = rule.source_field
        if rule.xpath:
            # Regex to get the last part of an XPath, handling attributes like @name
            match = re.search(r'/([^/@]+|@[^/]+)$', rule.xpath)
            if match:
                simple_source_field_name = match.group(1)
            else:
                simple_source_field_name = rule.source_field # Fallback if regex fails

        csv_context = self._build_csv_context_for_rule(rule, simple_source_field_name)
        csv_context_text = json.dumps(csv_context, indent=2) if csv_context else "No matching tag samples found in data/agile_payload.csv."

        prompt = f"""
        You are an expert data engineer. Your task is to convert a natural language data mapping rule into a set of precise, machine-readable validation steps in JSON.

        Analyze the following rule information:
        - Rule ID: {rule.id}
        - Rule Name: {rule.name}
        - Severity (metadata only): {rule.severity}
        - Description: "{rule.description}"
        - Source Field for static checks: {rule.source_field}
        - Type (expected data type for the CSV value): {rule.type}
        - Required (value must be present in data/agile_payload.csv): {rule.required}
        - Max Length (character limit for the value): {rule.max_length}
        - Target Structure: {rule.target['structure'] if rule.target else 'N/A'}
        - Target Field: {rule.target['field'] if rule.target else 'N/A'}
        - XPath: {rule.xpath}
        - CSV Tag Samples (from data/agile_payload.csv) for related fields: {csv_context_text}

        Generate the corresponding validation rules based on the description and the structured attributes above.
        - Focus on validating the value from data/agile_payload.csv: use 'type' to create TYPE_CHECK rules (expected_value should be the type label or a clear description of the expected type), 'required' to create REQUIRED_CHECK rules (value must exist), and 'max_length' to create LENGTH_CHECK rules with the character limit as a string.
        - Always populate 'expected_value' for every rule you generate. If sample values for a tag are available above, use the first sample value as the expected_value for checks about that tag (e.g., VALUE_MAPPING).
        - Severity is provided for completeness but does not need to drive additional checks.
        - When creating 'REQUIRED_CHECK', 'LENGTH_CHECK', or 'DEFAULT_VALUE' rules, the 'source_column' should be the simple name of the field (the last part of the XPath, or the 'Source Field' directly). For example, for an XPath like `//Product/ProductInternalID`, the `source_column` is 'ProductInternalID'. For an XPath like `//Product/@id`, the `source_column` is '@id'.
        - For 'VALUE_MAPPING' rules, the 'source_column' is the primary field being validated, and 'target_column' is the field it should be compared against. Both should be the simple field names. For instance, if the description says "Additionally map the field value to ReceiverProductInternalID (Product->ReceiverProductInternalID)", then `source_column` would be 'ProductInternalID' and `target_column` would be 'ReceiverProductInternalID'. Do not emit a VALUE_MAPPING rule without a target_column.
        - For 'VALUE_MAPPING' rules, set 'expected_value' to the expected target field value when sample data is available; otherwise, set a clear textual expectation like "Match ReceiverProductInternalID". If the description references a tag that exists in the CSV sample data above, assume that tag should be the target_column.
        - Ensure 'expected_value' for 'LENGTH_CHECK' is a string representation of the maximum length.
        - Consider the `XPath` `{rule.xpath}` and its implied simple field name '{simple_source_field_name}' when determining `source_column`.
        """
        # print(f"DEBUG: Prompt for rule {rule.id}:\n{prompt}") # Debugging line

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "create_validation_rules"}},
                temperature=0.0, # For more deterministic output
            )
            
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                print(f"Warning: AI did not produce a function call for rule '{rule.id}'.")
                return []

            function_args = json.loads(tool_calls[0].function.arguments)
            raw_rules = function_args.get("rules", [])

            # Normalize certain rule fields post-AI to ensure consistency with XPath-derived names
            normalized_rules = []
            for r in raw_rules:
                # Force source_column to the simple XPath field for basic checks
                if r.get("type") in ("REQUIRED_CHECK", "LENGTH_CHECK", "TYPE_CHECK") and simple_source_field_name:
                    r["source_column"] = simple_source_field_name
                normalized_rules.append(r)
            
            # The AI now provides all necessary fields, including id and severity
            executable_rules = [ExecutableRule(**r) for r in normalized_rules]
            
            print(f"Successfully interpreted rule '{rule.id}' into {len(executable_rules)} executable steps.")
            self._cache[cache_key] = executable_rules
            return executable_rules

        except (openai.APIError, json.JSONDecodeError) as e:
            print(f"Error interpreting rule '{rule.id}': {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred for rule '{rule.id}': {e}")
            return []
