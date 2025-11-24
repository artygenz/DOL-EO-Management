from __future__ import annotations

"""Pre-router adapter: delegates classification to classifier strategies.

This module acts as a thin facade for legacy callers while keeping
message-understanding logic centralized in `classifiers.py`.
"""

from typing import Dict, List
from .logger import log_call
from .openai_client import get_openai_client
from .config import BrainConfig
from .classifiers import LLMClassifier


@log_call("pre_router.classify")
def classify(message: str) -> Dict[str, List[str]]:
    """Return {'entity': str, 'intents': [..], 'hints': {...}} using unified classifier stack."""
    try:
        config = BrainConfig.from_env()
        client = get_openai_client()
        if client:
            class _ClientAdapter:
                def __init__(self, raw):
                    self._raw = raw
                def create_completion(self, messages, model="gpt-4o-mini", tools=None, **kwargs):
                    return self._raw.chat.completions.create(model=model, messages=messages, tools=tools, **kwargs)
            clf = LLMClassifier(_ClientAdapter(client), config)
            result = clf.classify(message or "")
            return {"entity": result.entity, "intents": result.intents, "hints": result.hints}
        # No client available → safe default
        return {"entity": "tasks", "intents": ["search"], "hints": {}}
    except Exception:
        # Safe default
        return {"entity": "tasks", "intents": ["search"], "hints": {}}


