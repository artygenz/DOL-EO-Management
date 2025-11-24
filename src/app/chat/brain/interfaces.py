"""Brain component interfaces following Dependency Inversion Principle."""

from __future__ import annotations
from typing import Any, Dict, List, Protocol, Tuple
from abc import ABC, abstractmethod


class MessageClassifier(Protocol):
    """Interface for message classification."""
    
    def classify(self, message: str) -> Dict[str, Any]:
        """Classify user message into entity, intents, and hints."""
        ...


class ToolSelector(Protocol):
    """Interface for tool selection."""
    
    def select_tools(self, db: Any, user: Any, entity: str, intents: List[str]) -> Tuple[Dict[str, Any], List[Dict], str]:
        """Select appropriate tools for given entity and intents."""
        ...


class QueryExecutor(Protocol):
    """Interface for query execution."""
    
    def execute(
        self, 
        message: str, 
        tool_fns: Dict[str, Any], 
        tool_specs: List[Dict],
        context: Dict[str, Any] | None = None,
        hints: Dict[str, Any] | None = None,
        entity: str | None = None
    ) -> Dict[str, Any]:
        """Execute a query using selected tools."""
        ...


class LLMClient(Protocol):
    """Interface for LLM interactions."""
    
    def create_completion(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] | None = None,
        **kwargs
    ) -> Any:
        """Create a completion with optional function calling."""
        ...


class ResponseGenerator(Protocol):
    """Interface for response generation."""
    
    def generate_response(self, context: Any) -> str | None:
        """Generate natural language response from context."""
        ...


# Abstract base classes for concrete implementations

class BaseMessageClassifier(ABC):
    """Base class for message classifiers."""
    
    @abstractmethod
    def classify(self, message: str) -> Dict[str, Any]:
        pass


class BaseQueryExecutor(ABC):
    """Base class for query executors."""
    
    def __init__(self, llm_client: LLMClient, response_generator: ResponseGenerator):
        self._llm_client = llm_client
        self._response_generator = response_generator
    
    @abstractmethod
    def execute(self, message: str, tool_fns: Dict[str, Any], tool_specs: List[Dict], **kwargs) -> Dict[str, Any]:
        pass
