"""Message classification strategies following Strategy Pattern."""

from __future__ import annotations
from typing import Dict, List, Tuple, Any
import re
from datetime import date, timedelta
from dataclasses import dataclass

from .interfaces import MessageClassifier, LLMClient
from .config import BrainConfig


@dataclass(frozen=True)
class ClassificationResult:
    """Immutable classification result."""
    entity: str
    intents: List[str]
    hints: Dict[str, Any]
    confidence: int


class HeuristicClassifier:
    """Fast heuristic-based message classification."""
    
    UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
    
    def classify(self, message: str) -> ClassificationResult:
        """Classify message using heuristics."""
        msg = (message or "").lower()
        entity, e_score = self._detect_entity(msg)
        intents, i_score = self._detect_intent(msg)
        hints = self._extract_hints(msg)
        confidence = e_score + i_score
        
        return ClassificationResult(
            entity=entity,
            intents=intents,
            hints=hints,
            confidence=confidence
        )
    
    def _detect_entity(self, msg: str) -> Tuple[str, int]:
        """Detect entity type with confidence score."""
        # Priority: task-related queries in EO context
        if any(phrase in msg for phrase in ["tasks under my eos", "tasks in my eos", "tasks under my", "tasks in my"]):
            return "tasks", 3
        if any(phrase in msg for phrase in ["updates for my eos", "updates under my eos", "updates for my", "updates under my"]):
            return "task_updates", 3
        
        # Standard entity detection
        if any(w in msg for w in ["update", "updates", "progress", "blocker", "risk"]):
            return "task_updates", 2
        if any(w in msg for w in ["eo ", "executive order", "orders", "portfolio"]):
            return "executive_orders", 2
        if any(w in msg for w in ["pmo", "assignment", "assigned to pmo"]):
            return "eo_pmo", 2
        if any(w in msg for w in ["user", "executor", "reviewer", "admin", "people", "teammate"]):
            return "users", 1
        return "tasks", 0
    
    def _detect_intent(self, msg: str) -> Tuple[List[str], int]:
        """Detect intent types with confidence score."""
        intents: List[str] = ["search"]
        score = 1

        # Timeseries patterns
        if any(w in msg for w in ["trend", "over time", "per week", "timeseries", "weekly", "daily", "timeline", "time series", "history"]):
            intents.append("timeseries")
            score = 2

        # Aggregate patterns
        if any(w in msg for w in ["count", "how many", "aggregate", "group", "top", "leaderboard", "breakdown", "summary", "overview", "rank"]):
            if "aggregate" not in intents:
                intents.append("aggregate")
            score = 2

        # Detail patterns
        if any(w in msg for w in ["detail", "details", "show", "exact", "specific", "this id", "eo ", "task ", "update "]):
            if "detail" not in intents:
                intents.append("detail")
            score = max(score, 1 + (1 if self.UUID_RE.search(msg) else 0))

        # Canonical ordering
        order = {"search": 0, "detail": 1, "aggregate": 2, "timeseries": 3}
        unique = []
        for intent in intents:
            if intent not in unique:
                unique.append(intent)
        unique.sort(key=lambda x: order.get(x, 99))
        
        return unique, score
    
    def _extract_hints(self, msg: str) -> Dict[str, Any]:
        """Extract query hints from message."""
        hints: Dict[str, Any] = {}
        
        # UUID detection
        uuid_match = self.UUID_RE.search(msg)
        if uuid_match:
            uid = uuid_match.group(0)
            if "eo" in msg:
                hints["eo_id"] = uid
            elif "task" in msg:
                hints["task_id"] = uid
            elif "update" in msg:
                hints["update_id"] = uid

        # Status and flags
        if "blocker" in msg:
            hints["has_blockers"] = True
        if "risk" in msg:
            hints["has_risks"] = True
        
        # Status mapping
        status_patterns = {
            "in_progress": ["in progress", "inprogress"],
            "approved": ["approved"],
            "pending": ["pending"]
        }
        
        for status, patterns in status_patterns.items():
            if any(pattern in msg for pattern in patterns):
                hints["status"] = status
                break

        # Category detection
        categories = ["compliance", "legal", "finance", "security"]
        for category in categories:
            if category in msg and "status" not in hints:
                hints["category"] = category
                break

        # Date range extraction
        self._add_date_hints(msg, hints)
        
        return hints
    
    def _add_date_hints(self, msg: str, hints: Dict[str, Any]) -> None:
        """Add date-related hints."""
        today = date.today()
        
        if any(phrase in msg for phrase in ["last 7 days", "past week", "last week"]):
            hints["date_from"] = (today - timedelta(days=7)).isoformat()
            hints["date_to"] = today.isoformat()
        elif any(phrase in msg for phrase in ["this week", "current week", "recent updates this week"]):
            start = today - timedelta(days=today.weekday())
            hints["date_from"] = start.isoformat()
            hints["date_to"] = today.isoformat()


class LLMClassifier:
    """LLM-based message classification with few-shot examples and keyword mapping."""
    
    def __init__(self, llm_client: LLMClient, config: BrainConfig):
        self._llm_client = llm_client
        self._config = config
    
    def classify(self, message: str) -> ClassificationResult:
        """Classify message using LLM."""
        system_prompt = self._build_system_prompt()
        
        try:
            response = self._llm_client.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0
            )
            
            content = (response.choices[0].message.content or "").strip()
            return self._parse_llm_response(content)
            
        except Exception:
            # Graceful fallback to default
            return ClassificationResult(
                entity="tasks",
                intents=["search"],
                hints={},
                confidence=1
            )
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for LLM classification with few-shot examples."""
        return """You are a message classifier for a task management system. Classify user messages into JSON format.

ENTITY MAPPING (choose one):
- tasks: task, tasks, assignment, assignments, my tasks, task list, overdue tasks, pending tasks
- task_updates: update, updates, progress, blocker, blockers, risk, risks, task progress, status update
- executive_orders: EO, EOs, executive order, executive orders, order, orders, portfolio, portfolios
- users: user, users, people, person, executor, executors, reviewer, reviewers, admin, admins, teammate
- eo_pmo: PMO, PMOs, assignment, assignments, assigned to PMO, PMO assignment

INTENT MAPPING (choose one or more):
- search: find, list, show, get, search, what are, which, where
- detail: detail, details, specific, exact, this, particular, show me
- aggregate: count, how many, total, number of, summary, overview, breakdown, group by, top, most
- timeseries: trend, over time, per week, per day, timeline, history, weekly, daily, time series

FEW-SHOT EXAMPLES:

User: "what are total number of EOs?"
Response: {"entity": "executive_orders", "intents": ["aggregate"], "hints": {}}

User: "show me my tasks"
Response: {"entity": "tasks", "intents": ["search"], "hints": {}}

User: "list task updates with blockers"
Response: {"entity": "task_updates", "intents": ["search"], "hints": {"has_blockers": true}}

User: "how many users are there?"
Response: {"entity": "users", "intents": ["aggregate"], "hints": {}}

User: "tasks assigned to Kevin Brown"
Response: {"entity": "tasks", "intents": ["search"], "hints": {"users": "Kevin Brown"}}

User: "executive orders about compliance"
Response: {"entity": "executive_orders", "intents": ["search"], "hints": {"category": "compliance"}}

User: "task progress over the last week"
Response: {"entity": "task_updates", "intents": ["timeseries"], "hints": {"date_from": "last_week_start", "date_to": "today"}}

User: "PMO assignments for this quarter"
Response: {"entity": "eo_pmo", "intents": ["search"], "hints": {}}

User: "Show tasks by category"
Response: {"entity": "tasks", "intents": ["aggregate"], "hints": {"group_by": "category"}}

User: "Show tasks by status"
Response: {"entity": "tasks", "intents": ["aggregate"], "hints": {"group_by": "status"}}

User: "Show tasks under my EOs"
Response: {"entity": "tasks", "intents": ["search"], "hints": {}}

User: "Tasks due this week under my EOs"
Response: {"entity": "tasks", "intents": ["search"], "hints": {"due_this_week": true}}

User: "Search tasks in my EOs where category contains compliance"
Response: {"entity": "tasks", "intents": ["search"], "hints": {"category": "compliance"}}

User: "Show updates with blockers and risks for my EOs"
Response: {"entity": "task_updates", "intents": ["search"], "hints": {"has_blockers": true, "has_risks": true}}

User: "Latest update per task under my EOs"
Response: {"entity": "task_updates", "intents": ["search"], "hints": {}}

User: "Show details of my task with the nearest due date"
Response: {"entity": "tasks", "intents": ["search"], "hints": {"nearest_due": true}}

User: "My recent updates this week"
Response: {"entity": "task_updates", "intents": ["search"], "hints": {"date_from": "this_week_start", "date_to": "today"}}

KEYWORD PRIORITY RULES:
1. If message contains "tasks under my EOs" or "tasks in my EOs" → entity = "tasks"
2. If message contains "updates for my EOs" or "updates under my EOs" → entity = "task_updates"
3. If message contains "EO", "executive order", "order" (but NOT "tasks under" or "updates for") → entity = "executive_orders"
4. If message contains "update", "progress", "blocker", "risk" → entity = "task_updates"  
5. If message contains "PMO", "assignment" → entity = "eo_pmo"
6. If message contains "user", "executor", "reviewer", "admin" → entity = "users"
7. If message contains "count", "how many", "total", "number of" → intents = ["aggregate"]
8. If message contains "trend", "over time", "timeline" → intents = ["timeseries"]
9. If message contains "by category" → hints = {"group_by": "category"}
10. If message contains "by status" → hints = {"group_by": "status"}

DATE HANDLING:
- Use relative terms like "today", "this_week_start", "last_week_start" instead of hardcoded dates
- For "this week" queries, use {"date_from": "this_week_start", "date_to": "today"}
- For "last week" queries, use {"date_from": "last_week_start", "date_to": "today"}

Return JSON only with entity, intents (array), and hints (object)."""
    
    def _parse_llm_response(self, content: str) -> ClassificationResult:
        """Parse LLM JSON response."""
        import json
        
        try:
            obj = json.loads(content)
            return ClassificationResult(
                entity=obj.get("entity", "tasks"),
                intents=obj.get("intents", ["search"]),
                hints=obj.get("hints", {}),
                confidence=2  # LLM always high confidence
            )
        except Exception:
            return ClassificationResult(
                entity="tasks",
                intents=["search"],
                hints={},
                confidence=1
            )


class CompositeClassifier(MessageClassifier):
    """Composite classifier using heuristics + LLM fallback."""
    
    def __init__(self, llm_client: LLMClient, config: BrainConfig):
        self._heuristic = HeuristicClassifier()
        self._llm = LLMClassifier(llm_client, config)
        self._config = config
    
    def classify(self, message: str) -> Dict[str, Any]:
        """Classify using heuristics first, LLM fallback if confidence low."""
        result = self._heuristic.classify(message)
        
        # Use LLM fallback if confidence too low
        if (result.confidence < self._config.confidence_threshold and 
            self._config.enable_llm_fallback):
            result = self._llm.classify(message)
        
        return {
            "entity": result.entity,
            "intents": result.intents,
            "hints": result.hints
        }
