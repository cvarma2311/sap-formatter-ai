import re
import pandas as pd
from typing import List, Dict, Any, Optional
from data_models import ExecutableRule, ValidationResult # Ensure data_models is correctly imported

class Validator:
    """
    Executes a list of machine-readable rules against a preprocessed data structure
    derived from the flattened XML/CSV.
    """

    def __init__(self, raw_dataframe: pd.DataFrame):
        self.raw_df = raw_dataframe
        self.processed_data: List[Dict[str, Any]] = []
        if not self.raw_df.empty:
            print(f"Validator initialized with raw DataFrame of shape {self.raw_df.shape}.")
            self.processed_data = self._preprocess_data()
            print(f"Preprocessed into {len(self.processed_data)} logical records.")
        else:
            print("Validator initialized with an empty DataFrame. No data to preprocess.")

    def _preprocess_data(self) -> List[Dict[str, Any]]:
        """
        Transforms the 'long' format raw_df (XML node list) into a list of 'wide' format
        dictionaries, where each dictionary represents a logical record (e.g., a Product,
        MessageHeader, etc.) and its direct child element/attribute key-value pairs.

        It groups nodes by their 'parent_id' to reconstruct logical records.
        Handles multiple occurrences of the same tag under a parent by storing them as a list.
        """
        if self.raw_df.empty:
            return []

        processed_records = []
        
        # Filter out rows without a value to simplify processing, and create a copy to avoid SettingWithCopyWarning
        data_with_values = self.raw_df[self.raw_df['value'].notna()].copy()
        data_with_values = data_with_values[data_with_values['value'] != ''].copy()

        # Handle root level elements first (where parent_id is NaN)
        root_elements = data_with_values[data_with_values['parent_id'].isna()]
        for _, row in root_elements.iterrows():
            processed_records.append({
                '_node_id': row['node_id'],
                '_parent_path': row['parent_path'] if pd.notna(row['parent_path']) else 'Root',
                'tag': row['tag'],
                'value': row['value']
            })

        # Group by parent_id to gather all fields belonging to one logical entity
        # This assumes that elements with the same parent_id are siblings within a record.
        grouped_by_parent = data_with_values[data_with_values['parent_id'].notna()].groupby('parent_id')

        for parent_id, group in grouped_by_parent:
            # Get the actual 'path' of the parent for better context
            parent_node_row = self.raw_df[self.raw_df['node_id'] == parent_id]
            parent_path_of_record = parent_node_row.iloc[0]['path'] if not parent_node_row.empty else f"ID_{parent_id}"
            
            record = {'_parent_id': parent_id, '_parent_path': parent_path_of_record}
            
            for _, row in group.iterrows():
                tag = row['tag']
                value = row['value']
                
                # If a tag appears multiple times under the same parent, store as a list
                if tag in record:
                    if isinstance(record[tag], list):
                        record[tag].append(value)
                    else:
                        record[tag] = [record[tag], value] # Convert to list
                else:
                    record[tag] = value
            processed_records.append(record)

        return processed_records

    def _get_field_value(self, record: Dict[str, Any], field_name: str) -> Optional[str]:
        """Helper to safely get a field value from a record, handling lists by returning the first item."""
        value = record.get(field_name)
        if isinstance(value, list):
            return str(value[0]) if value else None # Return first item for simplicity, or handle as needed
        return str(value) if value is not None else None

    def _generate_single_result(self, record_identifier: Any, record: Dict[str, Any], rule: ExecutableRule, message: str, expected_val: Any, actual_val: Any, status: str = 'Fail') -> ValidationResult:
        """Generates a single ValidationResult object."""
        # Use '_parent_path' or a unique identifier from the record for context in reporting
        context_identifier = record.get('_parent_path', f"Record_Idx_{record_identifier}")
        return ValidationResult(
            rule_id=rule.id if hasattr(rule, 'id') else 'N/A',
            severity=rule.severity if hasattr(rule, 'severity') else 'E',
            status=status,
            csv_row=context_identifier, # Use a more meaningful identifier
            csv_column=rule.source_column,
            field_value=str(actual_val) if actual_val is not None else "N/A",
            expected=str(expected_val) if expected_val is not None else "N/A",
            actual=str(actual_val) if actual_val is not None else "N/A",
            message=message
        )

    def _validate_required(self, record_identifier: Any, record: Dict[str, Any], rule: ExecutableRule) -> Optional[ValidationResult]:
        """Checks for missing values in a required field for a single record."""
        field_name = rule.source_column
        value = self._get_field_value(record, field_name)
        if value is None or value == '':
            return self._generate_single_result(
                record_identifier, record, rule, 
                f"Field '{field_name}' is required but is missing or empty.", 
                "Not Null or Empty", value
            )
        return None

    def _validate_length(self, record_identifier: Any, record: Dict[str, Any], rule: ExecutableRule) -> Optional[ValidationResult]:
        """Checks if string length exceeds the maximum allowed for a single record."""
        field_name = rule.source_column
        value = self._get_field_value(record, field_name)
        max_len = int(rule.expected_value) # expected_value stores max_length for this rule type

        if value is not None and len(value) > max_len:
            return self._generate_single_result(
                record_identifier, record, rule, 
                f"Length of field '{field_name}' ('{value}') exceeds maximum of {max_len}.", 
                f"<= {max_len}", value
            )
        return None

    def _validate_value_mapping(self, record_identifier: Any, record: Dict[str, Any], rule: ExecutableRule) -> Optional[ValidationResult]:
        """Checks if the value in a source field matches the value in a target field for a single record."""
        source_field = rule.source_column
        target_field = rule.target_column # Assuming target_column is added to ExecutableRule for this type
        
        source_value = self._get_field_value(record, source_field)
        target_value = self._get_field_value(record, target_field)

        if source_value is None or target_value is None:
            # If either field is missing, it's a failure for value mapping if both are expected
            # This logic might need refinement based on exact requirements.
            # For now, if one is missing, they can't match.
            if source_value != target_value: # Only report if they are actually different
                return self._generate_single_result(
                    record_identifier, record, rule, 
                    f"One or both fields for value mapping are missing. '{source_field}': '{source_value}', '{target_field}': '{target_value}'.",
                    f"Value of '{target_field}'", f"Value of '{source_field}'"
                )
            return None # If both are None, they match (e.g., optional fields)

        if source_value != target_value:
            return self._generate_single_result(
                record_identifier, record, rule, 
                f"Value of '{source_field}' ('{source_value}') does not match value of '{target_field}' ('{target_value}').", 
                target_value, source_value
            )
        return None

    def _validate_type(self, record_identifier: Any, record: Dict[str, Any], rule: ExecutableRule) -> Optional[ValidationResult]:
        """
        Performs a basic type check based on the expected_value label.
        Currently supports simple CHAR (string) and NUMERIC checks.
        """
        field_name = rule.source_column
        value = self._get_field_value(record, field_name)

        if value is None:
            return self._generate_single_result(
                record_identifier, record, rule,
                f"Field '{field_name}' is missing; cannot perform type check.",
                rule.expected_value, value
            )

        expected = (rule.expected_value or "").strip().lower()
        if expected in ("char", "string"):
            # Any string is acceptable; if present, pass.
            return None
        if expected in ("num", "numeric", "number", "int", "integer"):
            if re.fullmatch(r"-?\d+(\.\d+)?", value):
                return None
            return self._generate_single_result(
                record_identifier, record, rule,
                f"Field '{field_name}' value '{value}' is not numeric.",
                "Numeric", value
            )
        # Unknown expected type: treat as pass to avoid noisy failures
        return None

    def execute(self, rules: List[ExecutableRule]) -> List[ValidationResult]:
        """
        Runs all validation rules against the processed data and returns a list of failure results.
        """
        all_results = []
        if not self.processed_data:
            print("No logical records to validate. Skipping validation.")
            return all_results

        rule_dispatch_map = {
            'REQUIRED_CHECK': self._validate_required,
            'LENGTH_CHECK': self._validate_length,
            'VALUE_MAPPING': self._validate_value_mapping,
            'TYPE_CHECK': self._validate_type,
            # Add other rule types here
        }

        print(f"Executing {len(rules)} validation rules against {len(self.processed_data)} records...")
        
        for rule in rules:
            rule_applied = False
            for record_id, record in enumerate(self.processed_data):
                field_to_check_presence = rule.source_column

                # Apply rules only to records that contain the relevant tags
                if rule.type == 'VALUE_MAPPING':
                    has_source = field_to_check_presence in record
                    has_target = rule.target_column in record if rule.target_column else False
                    if not (has_source or has_target):
                        continue
                else:
                    if field_to_check_presence not in record:
                        continue

                validator_func = rule_dispatch_map.get(rule.type)
                if not validator_func:
                    print(f"Warning: Unknown rule type '{rule.type}'. Skipping rule ID '{rule.id}'.")
                    break

                rule_applied = True
                result = validator_func(record_id, record, rule)
                if result:
                    all_results.append(result)
                    break  # Only report one result per rule
                else:
                    # Record a passing validation for the first applicable record
                    expected = rule.expected_value if rule.expected_value is not None else ""
                    source_val = self._get_field_value(record, rule.source_column)
                    target_val = self._get_field_value(record, rule.target_column) if rule.target_column else None
                    if rule.type == 'VALUE_MAPPING':
                        msg = f"Values match for '{rule.source_column}' and '{rule.target_column}'."
                        expected_out = target_val if target_val is not None else expected
                        actual_out = source_val
                    elif rule.type == 'LENGTH_CHECK':
                        msg = f"Length of '{rule.source_column}' within allowed maximum {expected}."
                        expected_out = expected
                        actual_out = source_val
                    elif rule.type == 'REQUIRED_CHECK':
                        msg = f"Field '{rule.source_column}' is present."
                        expected_out = expected or "Not Null or Empty"
                        actual_out = source_val
                    elif rule.type == 'TYPE_CHECK':
                        msg = f"Field '{rule.source_column}' matches expected type '{expected}'."
                        expected_out = expected
                        actual_out = source_val
                    else:
                        msg = "Validation passed."
                        expected_out = expected
                        actual_out = source_val

                    all_results.append(self._generate_single_result(
                        record_id, record, rule, msg, expected_out, actual_out, status='Pass'
                    ))
                    break  # Only report one result per rule

            if not rule_applied:
                print(f"Warning: Rule ID '{rule.id}' could not be applied to any records (missing tags?).")
        
        num_failures = len([r for r in all_results if r.status == 'Fail'])
        print(f"Validation complete. Found {num_failures} failures across {len(all_results)} evaluated rules.")
        return all_results
