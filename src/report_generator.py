from typing import List
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from data_models import ValidationResult

class ReportGenerator:
    """Generates validation reports in various formats."""

    def __init__(self, results: List[ValidationResult]):
        self.results = results
        if self.results:
            self.df = pd.DataFrame([res.model_dump() for res in results])
        else:
            self.df = pd.DataFrame()
        print(f"ReportGenerator initialized with {len(results)} results.")

    def generate_html(self, template_path: str, output_path: str):
        """Generates an HTML report from a Jinja2 template."""
        if self.df.empty:
            print("No results to generate report.")
            # Still write a valid empty report
            html_content = "<h1>Validation Report</h1><p>No validation results to display.</p>"
        else:
            env = Environment(loader=FileSystemLoader('.'))
            template = env.get_template(template_path)
            html_content = template.render(
                results=self.results,
                title="Validation Report"
            )

        with open(output_path, 'w') as f:
            f.write(html_content)
        print(f"HTML report generated at {output_path}")

    def generate_csv(self, output_path: str):
        """Generates a CSV report."""
        if self.df.empty:
            print("No results to generate CSV.")
            return
            
        self.df.to_csv(output_path, index=False)
        print(f"CSV report generated at {output_path}")

    def generate_excel(self, output_path: str):
        """Generates an Excel report."""
        if self.df.empty:
            print("No results to generate Excel.")
            return

        self.df.to_excel(output_path, index=False)
        print(f"Excel report generated at {output_path}")
