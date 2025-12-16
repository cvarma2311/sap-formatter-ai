from typing import Tuple

from src.data_models import MappingRule


def _table_from_xpath(xpath: str) -> str:
    # Example: //Product/Item/Description -> Product
    trimmed = xpath.strip().lstrip("/").split("/")
    return trimmed[0] if trimmed else ""


def _field_from_xpath(xpath: str) -> str:
    # Use the deepest segment as field name
    trimmed = xpath.strip().rstrip("/").split("/")
    return trimmed[-1] if trimmed else ""


def resolve_identity(rule: MappingRule) -> Tuple[str, str]:
    """
    Resolve table_name and field_name deterministically.
    """
    table_name = ""
    field_name = ""
    if rule.xpath:
        table_name = _table_from_xpath(rule.xpath)
        field_name = _field_from_xpath(rule.xpath)
    if not table_name and rule.target and rule.target.structure:
        table_name = rule.target.structure
    if not field_name:
        field_name = rule.source_field or rule.target.field or ""
    return table_name, field_name

