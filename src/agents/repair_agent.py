from typing import Any, Dict


def attempt_repair(fragment: Dict[str, Any], error: str) -> Dict[str, Any]:
    """
    Simple repair hook. Currently passes through but annotates error for visibility.
    """
    repaired = dict(fragment)
    repaired["needs_review_error"] = error
    return repaired

