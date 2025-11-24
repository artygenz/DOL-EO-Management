from __future__ import annotations

import os
from src.db.session import SessionLocal
from src.models.user import User
from src.app.chat.brain.pre_router import classify
from src.app.chat.brain.selector import select_tools
from src.app.chat.brain.query_runner import run_query_with_tools

EMAILS_BY_ROLE = {
    "admin": "jack.smith@lumenlighthouse.ai",
    "reviewer": "kevin.brown@lumenlighthouse.ai",
    "executor": "ayesha.ahsan@lumenlighthouse.ai",
}

QUESTIONS = {
    "admin": [
        "How many executive orders do we have?",
        "Show EO status breakdown.",
        "Show tasks by category.",
        "How many total tasks do we have?",
        "Any updates with blockers or risks across the org?",
        "Top executors by updates this month.",
        "Show task completion trend this week.",
        "How many EOs were received this month?",
        "Show PMOs with the most EOs.",
        "Search tasks where category contains compliance",
    ],
    "reviewer": [
        "Show my executive orders.",
        "Show tasks under my EOs.",
        "Show updates with blockers and risks for my EOs.",
        "How many tasks in my portfolio by status?",
        "Tasks due this week under my EOs.",
        "Latest update per task under my EOs.",
        "Which executors are most active on my EOs?",
        "Search tasks in my EOs where category contains compliance",
    ],
    "executor": [
        "Show my tasks.",
        "My tasks in progress.",
        "Tasks due this week for me.",
        "My recently completed tasks.",
        "Show updates with blockers from my tasks.",
        "My recent updates this week.",
        "Search my tasks where category contains compliance",
        "Show details of my task with the nearest due date.",
    ],
}


def _get_user(db, role: str) -> User:
    email = EMAILS_BY_ROLE.get(role)
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    u = db.query(User).filter(User.role == role).first()
    if not u:
        raise RuntimeError(f"No user for role={role}")
    return u


def run_for_role(db, role: str):
    user = _get_user(db, role)
    context = {"role": getattr(user, "role", ""), "user_id": str(getattr(user, "id", ""))}
    print(f"\n===== ROLE: {role.upper()} =====")

    for q in QUESTIONS[role]:
        print(f"\n-- Q: {q}")
        route = classify(q)
        print("route:", route)

        entity = route.get("entity")
        intents = route.get("intents", ["search"]) or ["search"]
        hints = route.get("hints", {})

        tool_fns, tool_specs, selected_entity = select_tools(db, user, entity, intents)
        print("tools:", [spec["function"]["name"] for spec in tool_specs])

        out = run_query_with_tools(q, tool_fns, tool_specs, context=context, hints=hints, entity=selected_entity)
        if isinstance(out, dict):
            print("\n\n######################## RESPONSE - START ########################")
            if "tool" in out:
                print("tool:", out.get("tool"))
            if "args" in out:
                print("args:", out.get("args"))
            if "final" in out:
                print("\n\nLLM response:", out.get("final"))
                print("\n\n")
            if "data" in out:
                data = out["data"]
                if isinstance(data, dict):
                    keys = list(data.keys())
                    print("result keys:", keys)
                    for k in ("tasks", "updates", "executive_orders", "users"):
                        if k in data and isinstance(data[k], list):
                            print(f"{k} sample:", data[k][:2])
                            print(f"{k} total:", data.get("total"), f"{k} count:", len(data[k]))
                            break
                    # Handle aggregate data
                    if not any(k in data for k in ("tasks", "updates", "executive_orders", "users")):
                        print("aggregate data:", data)
                else:
                    print("data:", data)
            if "processing" in out:
                print("processing steps:", len(out["processing"]))
            print("######################## RESPONSE - END ########################\n\n")
        else:
            print(out)


def run():
    db = SessionLocal()
    try:
        for role in ("admin", "reviewer", "executor"):
            run_for_role(db, role)
    finally:
        db.close()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        run_for_role(db, 'admin')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.close()
