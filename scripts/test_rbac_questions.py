from __future__ import annotations

from src.db.session import SessionLocal
from src.models.user import User
from src.app.chat.brain.pre_router import classify
from src.app.chat.brain.selector import select_tools
from src.app.chat.brain.query_runner import run_query_with_tools, run_query_with_tools_streaming

EMAILS_BY_ROLE = {
    "admin": "jack.smith@lumenlighthouse.ai",
    "reviewer": "kevin.brown@lumenlighthouse.ai",
    "executor": "hibbi.iqbal@lumenlighthouse.ai",
}

TESTS = {
    # Admin can see everything
    "admin": [
        ("Show tasks by category.", True),
        ("List the task updates with blockers and risks", True),
        ("Show all executive orders", True),
    ],
    # Reviewer: should only see their EO scope
    "reviewer": [
        ("Show tasks under my EOs.", True),
        ("Show tasks under someone else's EO", False),
        ("Show updates with blockers and risks", True),
        ("Show all tasks", False),
    ],
    # Executor: should only see own tasks
    "executor": [
        ("Show my tasks.", True),
        ("Show tasks assigned to Kevin Brown", False),
        ("Show updates from my tasks", True),
        ("Show updates from Dylan's tasks", False),
    ],
}


LOG_LINES = []

def _get_user(db, role: str) -> User:
    u = db.query(User).filter(User.email == EMAILS_BY_ROLE[role]).first()
    if u:
        return u
    u = db.query(User).filter(User.role == role).first()
    if not u:
        raise RuntimeError(f"No user for role={role}")
    return u


def run_case(db, role: str, question: str, should_see: bool, use_streaming: bool = False):
    user = _get_user(db, role)
    ctx = {"role": user.role, "user_id": str(user.id)}

    route = classify(question)
    entity = route.get("entity")
    intents = route.get("intents", ["search"]) or ["search"]
    hints = route.get("hints", {})

    tool_fns, tool_specs, selected_entity = select_tools(db, user, entity, intents)
    
    if use_streaming:
        # Use streaming version
        out = None
        final_response = ""
        for result in run_query_with_tools_streaming(question, tool_fns, tool_specs, context=ctx, hints=hints, entity=selected_entity):
            out = result
            if "final_stream" in result:
                # Collect the streaming response
                for chunk in result["final_stream"]:
                    final_response += chunk
    else:
        # Use non-streaming version
        out = run_query_with_tools(question, tool_fns, tool_specs, context=ctx, hints=hints, entity=selected_entity)
        final_response = out.get("final", "")

    visible = False
    if isinstance(out, dict):
        data = out.get("data")
        resp = out.get("response")
        # Heuristics: non-empty list in preview or data indicates visibility
        if resp and isinstance(resp, dict):
            prev = resp.get("data_preview")
            visible = bool(prev and prev.get("total", 0) > 0)
        elif isinstance(data, dict):
            for k in ("tasks", "updates", "executive_orders", "users"):
                if k in data and isinstance(data[k], list) and len(data[k]) > 0:
                    visible = True
                    break

    status = "PASS" if visible == should_see else "FAIL"
    LOG_LINES.append(f"[{role}] {status}: '{question}' -> visible={visible}, expected={should_see}")
    LOG_LINES.append("route:" + str(route))
    LOG_LINES.append("tool:" + str(out.get("tool")))
    LOG_LINES.append("args:" + str(out.get("args")))
    LOG_LINES.append(f"\nLLM response ({'streaming' if use_streaming else 'non-streaming'}): {final_response}")
    LOG_LINES.append("\n\n")
    print(f"\n\n[{role}] {status}: '{question}' -> visible={visible}, expected={should_see}")
    print("route:", route)
    if isinstance(out, dict):
        print("tool:", out.get("tool"))
        print("args:", out.get("args"))
        print(f"\n\n LLM response ({'streaming' if use_streaming else 'non-streaming'}): {final_response}")
        # print("\nresponse_text:", (out.get("response") or {}).get("text"))
    print("\n\n")

def write_list_to_file(lines, filename="output.txt"):
    """
    Writes a list of strings to a text file in the current directory.

    :param lines: List of strings to write
    :param filename: Name of the file to write to (default: output.txt)
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        print(f"File '{filename}' written successfully in the current directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

def run():
    print("RBAC TESTS")
    db = SessionLocal()
    try:
        # Test non-streaming first
        print("\n" + "="*50)
        print("TESTING NON-STREAMING RESPONSES")
        print("="*50)
        for role, cases in TESTS.items():
            print(f"\n=== ROLE: {role.upper()} (Non-Streaming) ===")
            for q, ok in cases:
                run_case(db, role, q, ok, use_streaming=False)
        
        # Test streaming
        print("\n" + "="*50)
        print("TESTING STREAMING RESPONSES")
        print("="*50)
        for role, cases in TESTS.items():
            print(f"\n=== ROLE: {role.upper()} (Streaming) ===")
            for q, ok in cases:
                run_case(db, role, q, ok, use_streaming=True)
        
        write_list_to_file(LOG_LINES, "rbac_tests.txt")
    finally:
        db.close()


if __name__ == "__main__":
    run()
