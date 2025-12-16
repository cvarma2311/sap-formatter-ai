from typing import Any, Dict, Optional


class LLMClient:
    """
    Placeholder LLM client to allow dependency injection.
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def structured_completion(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("LLM client is disabled in this environment.")
        raise NotImplementedError("LLM client integration not implemented.")

