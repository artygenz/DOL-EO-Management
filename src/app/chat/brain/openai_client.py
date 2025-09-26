from __future__ import annotations

"""Shared OpenAI client for brain components.

- Lazily initializes a single client instance.
- Keeps construction in one place to simplify testing and swapping providers.
"""

from typing import Optional
from src.core.client_hub import get_openai_client as get_centralized_openai_client


def get_openai_client():
	"""Return a shared OpenAI client instance or None if unavailable.

	Uses centralized client hub for OpenAI client management.
	"""
	return get_centralized_openai_client()
