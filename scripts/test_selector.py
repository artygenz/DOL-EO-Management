from __future__ import annotations

import os
from pprint import pprint

from src.db.session import SessionLocal
from src.models.user import User
from src.app.chat.brain.selector import select_tools


def _get_any_user(db, role: str) -> User:
    q = db.query(User).filter(User.role == role).limit(1)
    u = q.first()
    if not u:
        raise RuntimeError(f"No user with role={role} found in DB")
    return u


def run():
    db = SessionLocal()
    try:
        # Pick a reviewer by default; change role if needed
        user = _get_any_user(db, role=os.getenv("TEST_ROLE", "reviewer"))

        scenarios = [
            ("tasks", ["search"]),
            ("tasks", ["aggregate"]),
            ("task_updates", ["search", "detail"]),
            ("executive_orders", ["search", "aggregate"]),
            ("users", ["search"]),
        ]

        for entity, intents in scenarios:
            print("\n-- entity=", entity, "intents=", intents)
            tool_fns, tool_specs = select_tools(db, user, entity, intents)
            print("tools count:", len(tool_specs))
            names = [spec["function"]["name"] for spec in tool_specs]
            print("tool names:", names)
            # Sanity: call a search tool with default args if present
            for name in names:
                if name.startswith("search_"):
                    print("calling", name)
                    out = tool_fns[name]({})
                    pprint({"tool": name, "keys": list(out.keys())})
                    break
    finally:
        db.close()


if __name__ == "__main__":
    run()


