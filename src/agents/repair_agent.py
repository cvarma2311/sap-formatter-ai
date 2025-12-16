from typing import Any, Dict


def attempt_repair(fragment: Dict[str, Any], error: str, allowed_enums: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Simple repair hook:
    - Lowercases enum-like strings if a whitelist is provided.
    - Annotates the fragment with the original error for downstream review.
    """
    repaired = dict(fragment)
    if allowed_enums:
        for key, allowed in allowed_enums.items():
            val = repaired.get(key)
            if isinstance(val, str):
                lowered = val.lower()
                matches = [opt for opt in allowed if str(opt).lower() == lowered]
                if matches:
                    repaired[key] = matches[0]
    repaired["needs_review_error"] = error
    return repaired
