# Implementation Plan: AI-Powered XML/CSV Validation Framework

This document outlines the phased implementation plan for building an advanced, AI-assisted validation framework for SAP data, similar in concept to enterprise tools like Ataccama.

## Phase 1: Project Setup and Foundational Components

This phase lays the groundwork for the entire application, focusing on environment, dependencies, and core data structures.

1.  **Environment and Dependencies:**
    *   **Structure:**
        ```
        sap-formatter-ai/
        ├───data/
        ├───feature_plans/
        ├───src/
        │   ├───__init__.py
        │   ├───main.py
        │   ├───data_models.py
        │   ├───rule_loader.py
        │   ├───xml_converter.py
        │   ├───ai_interpreter.py
        │   ├───validator.py
        │   └───report_generator.py
        ├───templates/
        │   └───report_template.html
        └───pyproject.toml
        ```
    *   **Dependencies:** `pyproject.toml` will manage dependencies: `pandas`, `pyyaml`, `lxml`, `pydantic`, `openai`, `jinja2`, `openpyxl`.

2.  **Core Data Models (`src/data_models.py`):**
    *   Use Pydantic to define strongly-typed, validated data structures for `MappingRule`, `ExecutableRule`, and `ValidationResult`. This is critical for data integrity throughout the application.

## Phase 2: Data Ingestion and Preparation

This phase focuses on getting the raw data (XML) and rules (YAML) into a usable in-memory format.

1.  **Rule Loader (`src/rule_loader.py`):**
    *   Implement a `RuleLoader` class to parse the `.yaml` rule file into a list of `MappingRule` Pydantic objects. Include robust error handling for file I/O and YAML parsing errors.

2.  **XML to Flattened CSV Converter (`src/xml_converter.py`):**
    *   Implement a memory-efficient `XMLConverter` using `lxml.etree.iterparse`.
    *   The core logic must correctly flatten the XML structure.
    *   **Multi-valued nodes** (e.g., multiple `<Characteristic>` elements for one product) must be handled by creating distinct rows in the output, duplicating the parent data for each instance. This de-normalizes the data into a relational format suitable for validation.

## Phase 3: AI-Assisted Rule Interpretation

This is the core AI-powered component of the project.

1.  **AI Rule Interpreter (`src/ai_interpreter.py`):**
    *   Create a `RuleInterpreter` class that takes an OpenAI API key.
    *   The main method, `interpret_rule`, will construct a detailed prompt for the OpenAI API (specifically a function-calling-capable model).
    *   **Prompt Engineering**: The prompt will provide the context (act as a data engineer), the specific `MappingRule` data, and a JSON Schema definition of the desired `ExecutableRule` output. This dramatically improves the reliability of the AI's response.
    *   **API Interaction**: The implementation will call the API and parse the returned JSON into Pydantic models. It must include error handling for API failures and invalid JSON responses.
    *   **Caching**: A dictionary-based cache will be used to store results for previously seen rule descriptions, saving cost and improving performance.

## Phase 4: Core Validation Engine

This module executes the machine-readable rules against the flattened data.

1.  **Validator (`src/validator.py`):**
    *   The `Validator` class will be initialized with the pandas DataFrame created from the flattened XML.
    *   The main `execute` method will iterate through the list of `ExecutableRule` objects.
    *   **Vectorized Operations**: For efficiency, the engine will use vectorized pandas operations to check for failures, rather than iterating row-by-row. For a given rule, it will first identify all failing rows and then generate `ValidationResult` objects only for those failures.
    *   **Rule Dispatcher**: A dispatcher will route each rule type to a specialized private method (e.g., `_validate_required`, `_validate_length`, `_validate_value_mapping`).

## Phase 5: Report Generation

This phase presents the validation outcomes in clear, human-readable formats.

1.  **Report Generator (`src/report_generator.py`):**
    *   The `ReportGenerator` class will take the list of `ValidationResult` objects as input.
    *   It will have methods to generate multiple output formats:
        *   `generate_html`: Use a Jinja2 template to create a rich, sortable, and color-coded HTML report.
        *   `generate_csv`, `generate_excel`, `generate_json`: For consumption by other systems or for data analysis.

## Phase 6: Orchestration

The final step ties all the modules into a single, executable workflow.

1.  **Main Script (`src/main.py`):**
    *   Use Python's `argparse` to create a user-friendly command-line interface.
    *   The `main` function will orchestrate the entire process: Load rules -> Convert XML -> Interpret Rules via AI -> Validate Data -> Generate Reports.
    *   It will include clear logging at each step and graceful handling of missing environment variables (like the `OPENAI_API_KEY`).
