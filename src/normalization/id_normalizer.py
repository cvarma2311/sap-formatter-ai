from src.data_models import FieldRule


def make_unique_id(table_name: str, field_name: str) -> str:
    return f"{table_name}.{field_name}"


def sort_field_rules(rules: list[FieldRule]) -> list[FieldRule]:
    """
    Stable ordering to enforce deterministic output.
    """
    return sorted(rules, key=lambda r: (r.table_name, r.field_name, r.unique_id))

