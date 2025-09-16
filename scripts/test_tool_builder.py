from __future__ import annotations

import json

from src.db.session import SessionLocal
from src.models.user import User

# Ensure tools are registered
import src.app.chat.tools  # noqa: F401
from src.app.chat.tool_builder import build_tools


def pretty(x):
    return json.dumps(x, indent=2, sort_keys=True, default=str)


def find_user_by_role(db, role: str) -> User | None:
    return db.query(User).filter(User.role == role, User.is_active == True).first()  # noqa: E712


def run():
    with SessionLocal() as db:
        reviewer = db.query(User).filter(User.email == "kevin.brown@lumenlighthouse.ai").first() or find_user_by_role(db, "reviewer")
        user = reviewer or find_user_by_role(db, "admin")
        assert user is not None, "Need a user to test tool builder"

        # Build tools for tasks search
        tool_fns, tool_specs = build_tools(db, user, entity="tasks", intents=["search"]) 
        print("Entity=tasks, intents=['search'] → tool names:")
        print([t["function"]["name"] for t in tool_specs])

        # Call one tool (search_tasks) with minimal args
        if "search_tasks" in tool_fns:
            res = tool_fns["search_tasks"]({"limit": 3, "offset": 0})
            print("\nsearch_tasks sample result (first 3):")
            print(pretty(res))

        # Build tools for task_updates aggregate/timeseries
        tool_fns2, tool_specs2 = build_tools(db, user, entity="task_updates", intents=["aggregate", "timeseries"]) 
        print("\nEntity=task_updates, intents=['aggregate','timeseries'] → tool names:")
        print([t["function"]["name"] for t in tool_specs2])


if __name__ == "__main__":
    run()


