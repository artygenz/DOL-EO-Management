"""Factory for creating brain components with proper dependency injection."""

from __future__ import annotations
from typing import Any

from .config import BrainConfig, DependencyContainer
from .interfaces import MessageClassifier, QueryExecutor
from .classifiers import CompositeClassifier
from .openai_client import get_openai_client
# Optional: Input validator can be added later when implemented
try:
    from .validation import InputValidator  # type: ignore
except Exception:  # pragma: no cover
    InputValidator = None  # type: ignore
from .logger import log_call


class OpenAIClientAdapter:
    """Adapter for OpenAI client to match LLMClient protocol."""
    
    def __init__(self, client: Any):
        self._client = client
    
    def create_completion(self, messages, tools=None, **kwargs):
        """Create completion with optional tools."""
        return self._client.chat.completions.create(
            messages=messages,
            tools=tools,
            **kwargs
        )


class BrainFactory:
    """Factory for creating brain components with proper DI."""
    
    @staticmethod
    def create_container(config: BrainConfig | None = None) -> DependencyContainer:
        """Create dependency container with all brain components."""
        if config is None:
            config = BrainConfig.from_env()
        
        container = DependencyContainer(config)
        
        # Register core components
        container.register("config", config)
        if InputValidator is not None:
            container.register("input_validator", InputValidator(max_length=1000))
        
        # Register LLM client
        openai_client = get_openai_client()
        if openai_client:
            llm_adapter = OpenAIClientAdapter(openai_client)
            container.register("llm_client", llm_adapter)
        
        return container
    
    @staticmethod
    def create_classifier(container: DependencyContainer) -> MessageClassifier:
        """Create message classifier with dependencies."""
        config = container.get("config")
        llm_client = container.get("llm_client")
        
        if llm_client and config.enable_llm_fallback:
            return CompositeClassifier(llm_client, config)
        else:
            # Return heuristic-only classifier
            from .classifiers import HeuristicClassifier
            
            class HeuristicOnlyWrapper:
                def __init__(self):
                    self._classifier = HeuristicClassifier()
                
                def classify(self, message: str):
                    result = self._classifier.classify(message)
                    return {
                        "entity": result.entity,
                        "intents": result.intents,
                        "hints": result.hints
                    }
            
            return HeuristicOnlyWrapper()
    
    @staticmethod
    def create_brain_pipeline(container: DependencyContainer | None = None) -> 'BrainPipeline':
        """Create complete brain pipeline."""
        if container is None:
            container = BrainFactory.create_container()
        
        classifier = BrainFactory.create_classifier(container)
        validator = container.get("input_validator")
        
        return BrainPipeline(
            classifier=classifier,
            validator=validator,
            container=container
        )


class BrainPipeline:
    """Main brain pipeline orchestrating all components."""
    
    def __init__(
        self,
        classifier: MessageClassifier,
        validator: InputValidator,
        container: DependencyContainer
    ):
        self._classifier = classifier
        self._validator = validator
        self._container = container
    
    @log_call("brain.pipeline.process")
    def process_message(
        self,
        message: str,
        db: Any,
        current_user: Any,
        **kwargs
    ) -> dict[str, Any]:
        """Process user message through complete brain pipeline."""
        # Validate input
        validation_result = self._validator.validate(message)
        if not validation_result.is_valid:
            return {
                "error": "Invalid input",
                "details": validation_result.errors,
                "final": "I couldn't process your request due to input validation errors."
            }
        
        sanitized_message = validation_result.sanitized_input
        
        # Classify message
        classification = self._classifier.classify(sanitized_message)
        
        # Select tools (using existing selector)
        from .selector import select_tools
        tool_fns, tool_specs, entity = select_tools(
            db, current_user, 
            classification["entity"], 
            classification["intents"]
        )
        
        # Execute query (using existing query runner)
        from .query_runner import run_query_with_tools
        context = kwargs.get("context", {})
        hints = classification["hints"]
        
        result = run_query_with_tools(
            sanitized_message,
            tool_fns,
            tool_specs,
            context=context,
            hints=hints,
            entity=entity
        )
        
        # Add classification info for debugging
        result["classification"] = classification
        result["validation_warnings"] = validation_result.warnings
        
        return result
