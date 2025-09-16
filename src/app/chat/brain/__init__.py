"""
Chat "brain" components:
- pre_router: classify message → {entity, intents, hints}
- selector: build a minimal tool set from registry for the chosen entity/intents
- query_runner: run one LLM function-calling step to execute a tool and return JSON

Import these and compose in your API route or higher-level agent.
"""


