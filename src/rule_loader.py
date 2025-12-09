import yaml
from typing import List
from data_models import MappingRule

class RuleLoader:
    """Loads mapping rules from a YAML or Excel file."""

    def load_from_yaml(self, file_path: str) -> List[MappingRule]:
        """
        Loads and parses rules from a YAML file that is expected to be a dictionary
        with a top-level 'rules' key containing the list of rule objects.
        """
        print(f"Loading rules from {file_path}...")
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Check if the loaded data is a dictionary and has the 'rules' key
        if not isinstance(data, dict) or 'rules' not in data:
            raise ValueError("YAML file should be a dictionary with a top-level 'rules' key.")

        raw_rules = data['rules']
        
        # Ensure the 'rules' key contains a list
        if not isinstance(raw_rules, list):
            raise ValueError("The 'rules' key in the YAML file should contain a list of rule objects.")

        rules = [MappingRule(**rule_data) for rule_data in raw_rules]
        print(f"Successfully loaded {len(rules)} rules.")
        return rules
