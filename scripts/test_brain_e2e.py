from __future__ import annotations

import os
from pprint import pprint

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

def _get_user(db, role: str) -> User:
    email = EMAILS_BY_ROLE.get(role)
    if email:
        u = db.query(User).filter(User.email == email).limit(1).first()
        if u:
            return u
    # Fallback by role
    u = db.query(User).filter(User.role == role).limit(1).first()
    if not u:
        raise RuntimeError(f"No user found for role={role} (email={email or 'N/A'})")
    return u

SAMPLES = [
    "Show my tasks",
    "List the task updates from executors which have blockers and risks",
    "Give me a portfolio overview",
    "Top executors by updates this month",
    # Additional NLG-friendly queries
    "What's the overall status of my executive orders?",
    "How are my teams performing on task completion?",
    "Can you analyze the trends in task updates this week?",
]

def run():
    db = SessionLocal()
    try:
        role = "reviewer"
        user = _get_user(db, role)
        context = {"role": getattr(user, "role", ""), "user_id": str(getattr(user, "id", ""))}

        for q in SAMPLES:
            print("\n-- Q:", q)
            route = classify(q)
            print("route:", route)

            entity = route.get("entity")
            intents = route.get("intents", ["search"]) or ["search"]
            hints = route.get("hints", {})

            tool_fns, tool_specs, selected_entity = select_tools(db, user, entity, intents)
            print("tools:", [spec["function"]["name"] for spec in tool_specs])

            out = run_query_with_tools(q, tool_fns, tool_specs, context=context, hints=hints, entity=selected_entity)
            # Print tool name, args, and formatted response
            if isinstance(out, dict):
                if "tool" in out:
                    print("tool:", out.get("tool"))
                if "args" in out:
                    print("args:", out.get("args"))
                
                # Print formatted response if available
                if "response" in out:
                    response = out["response"]
                    print("formatted text:", response.get("text", ""))
                    if response.get("data_preview"):
                        preview = response["data_preview"]
                        print(f"preview: {preview.get('total', 0)} total, showing {len(preview.get('rows', []))} rows")
                        if preview.get("rows"):
                            print("sample rows:", preview["rows"][:2])
                    if response.get("suggested_followups"):
                        print("followups:", response["suggested_followups"])
                
                # Fallback: show raw data if no formatted response
                elif "data" in out:
                    data = out["data"]
                    if isinstance(data, dict):
                        keys = list(data.keys())
                        print("result keys:", keys)
                        for k in ("tasks", "updates", "executive_orders", "users"):
                            if k in data and isinstance(data[k], list):
                                print(f"{k} sample:", data[k][:2])
                                try:
                                    print(f"{k} total:", data.get("total"), f"{k} count:", len(data[k]))
                                except Exception:
                                    pass
                                break
                    else:
                        print(data)
            else:
                print(out)
    finally:
        db.close()


if __name__ == "__main__":
    run()