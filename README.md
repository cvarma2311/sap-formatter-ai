# AI-Powered Data Validation Framework

This project is a sophisticated, AI-assisted framework designed to validate flat files (like CSVs generated from XML) against a set of rules defined in a YAML file. It leverages Large Language Models (LLMs) to interpret natural language descriptions in the rules, converting them into executable validation logic. The framework is inspired by enterprise-grade data governance tools like Ataccama and is built to be modular and extensible.

## ✨ Features

- **YAML-Driven Rules**: Define complex validation and mapping logic in a simple, human-readable YAML file.
- **AI-Powered Rule Interpretation**: Uses OpenAI's GPT models to convert natural language rule descriptions into machine-readable validation steps.
- **Advanced XML Flattening**: Intelligently converts complex, nested XML files into a flat, relational DataFrame, correctly handling one-to-many relationships.
- **Efficient Validation Engine**: Utilizes vectorized `pandas` operations for high-performance data validation.
- **Comprehensive Reporting**: Generates detailed validation reports in multiple formats (HTML, CSV, Excel) for easy analysis of failures.

## 📁 Project Structure

The repository is organized into several key directories:

```
sap-formatter-ai/
├───data/                 # Contains input artifacts like YAML rules and XML data.
│   ├───agile_mdg_rules.yaml
│   └───Agile_payload.xml
├───feature_plans/        # Markdown files describing the implementation plans for features.
├───reports/              # Default output directory for generated validation reports.
├───src/                  # All Python source code for the application.
│   ├───__init__.py
│   ├───main.py           # Main orchestration script and command-line interface.
│   ├───data_models.py    # Core Pydantic models for rules and results.
│   ├───rule_loader.py    # Module for loading rules from YAML files.
│   ├───xml_converter.py  # Handles the complex XML-to-DataFrame conversion.
│   ├───ai_interpreter.py # Interfaces with the OpenAI API to interpret rules.
│   ├───validator.py      # Executes the validation logic against the data.
│   └───report_generator.py # Generates the final validation reports.
├───templates/            # Jinja2 templates for generating HTML reports.
│   └───report_template.html
├───pyproject.toml        # Project definition and dependency list for Poetry.
└───README.md             # This file.
```

## 🚀 Installation and Setup Guide

This guide provides detailed steps for setting up the project environment, including shell configuration and dependency installation, tailored for macOS users.

### 1. macOS Environment Setup

These steps ensure your shell is correctly configured to work with modern Python tooling like Poetry.

#### Step 1.1: Set Zsh as the Default Shell

Modern macOS uses `zsh` as the default shell, but sometimes older profiles use `bash`. This project's tooling is configured for `zsh`.

1.  **Check your current shell:**
    ```sh
    echo $SHELL
    ```
    If the output is `/bin/zsh`, you can skip to the next step. If it is `/bin/bash`, proceed.

2.  **Change your default shell to Zsh:**
    You will be prompted for your password.
    ```sh
    chsh -s /bin/zsh
    ```

3.  **IMPORTANT: Close and restart your terminal application** for the change to take effect. In the new terminal, `echo $SHELL` should now report `/bin/zsh`.

4.  **Workaround (if needed):** If new terminals still open in `bash`, you can manually switch to `zsh` for your session by simply typing `zsh` and pressing Enter.

#### Step 1.2: Install Poetry

Poetry is used to manage the project's dependencies in a clean, isolated environment.

1.  **Run the official Poetry installer:**
    ```sh
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2.  **Configure your PATH:** The installer will prompt you to add a line to your shell's configuration file (`~/.zshrc`). Open it with a text editor:
    ```sh
    nano ~/.zshrc
    ```
    Add the following line to the end of the file:
    ```sh
    export PATH="/Users/your_username/.local/bin:$PATH" 
    ```
    *(Replace `your_username` with your actual username, or copy the exact line from the installer's output.)*

3.  **Save and Exit Nano:** Press `Ctrl+X`, then `Y` to confirm, then `Enter`.

4.  **Apply the changes** to your current terminal session:
    ```sh
    source ~/.zshrc
    ```

5.  **Verify the installation:**
    ```sh
    poetry --version
    ```
    You should see the Poetry version number.

### 2. Project Dependency Installation

Once your shell and Poetry are set up, you can install the project's Python libraries.

1.  **Clone the repository:**
    ```sh
    git clone <your-repository-url>
    cd sap-formatter-ai
    ```

2.  **Install dependencies:**
    ```sh
    poetry install
    ```
    This command reads the `pyproject.toml` file and installs all required libraries (like `pandas`, `openai`, etc.) into a dedicated virtual environment.

    *(Note: This project's `pyproject.toml` is configured with `package-mode = false`, which tells Poetry to only manage external dependencies, not the project's own source code. This is the correct setting for this type of application.)*

### 3. Configuration

For the AI-powered rule interpretation to work, you must set your OpenAI API key as an environment variable.

- **On macOS/Linux (in your `.zshrc` file for permanence):**
  ```sh
  export OPENAI_API_KEY='your-api-key-here'
  ```

- **On Windows (Command Prompt):**
  ```sh
  set OPENAI_API_KEY=your-api-key-here
  ```
- **On Windows (PowerShell):**
  ```sh
  $env:OPENAI_API_KEY="your-api-key-here"
  ```

If you do not set this key, you can still run the framework using the `--skip-ai` flag, but it will only perform static checks.

## 🏃‍♀️ How to Run

The application is run from the command line using the `src/main.py` script. Use `poetry run` to ensure you are using the correct virtual environment managed by Poetry.

### Basic Command

To run the validation with default file paths:
```sh
poetry run python src/main.py
```

### Command-Line Arguments

You can customize the execution with the following arguments:

| Argument         | Description                                                                 | Default                               |
| ---------------- | --------------------------------------------------------------------------- | ------------------------------------- |
| `--rules`        | Path to the YAML rules file.                                                | `data/agile_mdg_rules.yaml`           |
| `--xml`          | Path to the source XML data file.                                           | `data/Agile_payload.xml`              |
| `--record-tag`   | The XML tag that represents a single, high-level record.                    | `Product`                             |
| `--id`           | Run validation for a single, specific rule ID.                              | `None`                                |
| `--output-dir`   | The directory where validation reports will be saved.                       | `reports`                             |
| `--skip-ai`      | Run only static checks and skip the AI interpretation step.                 | `False`                               |

### Examples

**Run with custom file paths:**
```sh
poetry run python src/main.py --rules path/to/my_rules.yaml --xml path/to/my_data.xml
```

**Run for a single rule ID to debug it:**
```sh
poetry run python src/main.py --id "M-001"
```
*(This will also print the AI's interpretation of the rule to the console before running the validation.)*

**Run without using the AI features:**
```sh
poetry run python src.main.py --skip-ai
```

## 📊 Output

After a successful run, the `reports/` directory will contain the following files:

- `validation_report.html`: A detailed, easy-to-read report with color-coding for failed validations.
- `validation_report.csv`: A CSV file containing all validation failures.
- `validation_report.xlsx`: An Excel file with the same failure data.
