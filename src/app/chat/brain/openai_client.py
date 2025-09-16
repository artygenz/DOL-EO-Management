from __future__ import annotations

"""Shared OpenAI client for brain components.

- Lazily initializes a single client instance.
- Keeps construction in one place to simplify testing and swapping providers.
"""

from typing import Optional
import os

try:
	from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
	OpenAI = None  # type: ignore


_client: Optional[object] = None


def get_openai_client():
	"""Return a shared OpenAI client instance or None if unavailable.

	Respects OPENAI_API_KEY; if missing or SDK unavailable, returns None.
	"""
	global _client
	if _client is not None:
		return _client
	if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
		return None
	_client = OpenAI()
	return _client
