import re
from typing import List

from src.data_models import FilterEntry, FilterLogic, FilterOperator


def parse_filters(description: str) -> List[FilterEntry]:
    desc = description or ""
    clauses = re.split(r"\s+(and|or)\s+", desc, flags=re.IGNORECASE)
    results: List[FilterEntry] = []
    logic_next = FilterLogic.AND
    i = 0
    while i < len(clauses):
        part = clauses[i].strip()
        if part.lower() in ("and", "or"):
            logic_next = FilterLogic.AND if part.lower() == "and" else FilterLogic.OR
            i += 1
            continue
        text = part
        op = None
        field = None
        value = None
        if match := re.search(r"(\w+)\s*(=|==|equals|equal to)\s*'?(.*?)'?(?:\s|$)", text, re.IGNORECASE):
            field, _, value = match.groups()
            op = FilterOperator.EQUAL
        elif match := re.search(r"(\w+)\s*(!=|<>|not equals)\s*'?(.*?)'?(?:\s|$)", text, re.IGNORECASE):
            field, _, value = match.groups()
            op = FilterOperator.NOT_EQUAL
        elif match := re.search(r"(\w+)\s+contains\s+'?(.*?)'?", text, re.IGNORECASE):
            field, value = match.groups()
            op = FilterOperator.CONTAINS
        elif match := re.search(r"(\w+)\s+starts\s+with\s+'?(.*?)'?", text, re.IGNORECASE):
            field, value = match.groups()
            op = FilterOperator.STARTS_WITH
        elif match := re.search(r"(\w+)\s+ends\s+with\s+'?(.*?)'?", text, re.IGNORECASE):
            field, value = match.groups()
            op = FilterOperator.ENDS_WITH
        elif match := re.search(r"(\w+)\s+matches\s+regex\s+(.+)", text, re.IGNORECASE):
            field, value = match.groups()
            op = FilterOperator.REGEX
        elif match := re.search(r"(\w+)\s*(>=|greater than or equal to)\s*([0-9.]+)", text, re.IGNORECASE):
            field, _, value = match.groups()
            op = FilterOperator.GTE
        elif match := re.search(r"(\w+)\s*(>|greater than)\s*([0-9.]+)", text, re.IGNORECASE):
            field, _, value = match.groups()
            op = FilterOperator.GT
        elif match := re.search(r"(\w+)\s*(<=|less than or equal to)\s*([0-9.]+)", text, re.IGNORECASE):
            field, _, value = match.groups()
            op = FilterOperator.LTE
        elif match := re.search(r"(\w+)\s*(<|less than)\s*([0-9.]+)", text, re.IGNORECASE):
            field, _, value = match.groups()
            op = FilterOperator.LT

        if field and op:
            results.append(
                FilterEntry(
                    field=field,
                    operator=op,
                    value=value,
                    logic=logic_next if results else FilterLogic.AND,
                )
            )
        logic_next = FilterLogic.AND
        i += 1
    return results

