"""Configuration and dependency injection for brain components."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import os


@dataclass(frozen=True)
class BrainConfig:
    """Configuration for brain components."""
    
    # LLM Configuration
    openai_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    llm_temperature: float = 0.0
    llm_max_tokens: int = 300
    
    # Pre-router Configuration
    confidence_threshold: int = 2
    enable_llm_fallback: bool = True
    
    # Response Configuration
    max_preview_rows: int = 5
    max_followup_suggestions: int = 3
    
    # Logging Configuration
    enable_file_logging: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "BrainConfig":
        """Create configuration from environment variables."""
        return cls(
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "300")),
            confidence_threshold=int(os.getenv("PREROUTER_CONFIDENCE_THRESHOLD", "2")),
            enable_llm_fallback=os.getenv("ENABLE_LLM_FALLBACK", "true").lower() == "true",
            enable_file_logging=os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


class DependencyContainer:
    """Simple dependency injection container."""
    
    def __init__(self, config: BrainConfig):
        self.config = config
        self._instances: Dict[str, Any] = {}
    
    def register(self, key: str, instance: Any) -> None:
        """Register an instance."""
        self._instances[key] = instance
    
    def get(self, key: str) -> Any:
        """Get a registered instance."""
        return self._instances.get(key)
    
    def get_or_create(self, key: str, factory: callable) -> Any:
        """Get instance or create it using factory."""
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]
