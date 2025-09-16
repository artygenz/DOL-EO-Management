from __future__ import annotations

import argparse
import os
import sys
import glob
from typing import List

from src.db.session import SessionLocal
from src.models.user import User
from src.app.chat.brain.pre_router import classify
from src.app.chat.brain.selector import select_tools
from src.app.chat.brain.query_runner import DefaultQueryExecutor
from src.app.chat.brain.openai_client import get_openai_client
from src.app.chat.brain.config import BrainConfig


def find_user(db, email: str | None, role: str | None) -> User:
    if email:
        u = db.query(User).filter(User.email == email).limit(1).first()
        if u:
            return u
        raise RuntimeError(f"No user found with email={email}")
    if role:
        u = db.query(User).filter(User.role == role).limit(1).first()
        if u:
            return u
        raise RuntimeError(f"No user found for role={role}")
    raise RuntimeError("Either --email or --role must be provided")


def newest_chat_log_path() -> str | None:
    try:
        log_dir = "/app/logs/chat"
        paths = glob.glob(os.path.join(log_dir, "chat_debug_*.log"))
        if not paths:
            return None
        return max(paths, key=os.path.getmtime)
    except Exception:
        return None


def run_single_question(db, user: User, question: str) -> None:
    print(f"\nQ: {question}")
    context = {"role": getattr(user, "role", ""), "user_id": str(getattr(user, "id", ""))}
    route = classify(question)

    entity = route.get("entity")
    intents: List[str] = route.get("intents", ["search"]) or ["search"]
    hints = route.get("hints", {})

    tool_fns, tool_specs, selected_entity = select_tools(db, user, entity, intents)

    # Real-time progress printer
    def _print_progress(line: str) -> None:
        try:
            print(f".. {line}")
        except Exception:
            pass

    # Use class-based executor to stream progress
    exec_client = get_openai_client()
    executor = DefaultQueryExecutor(exec_client, config=BrainConfig.from_env())
    out = executor.execute(
        question,
        tool_fns,
        tool_specs,
        context=context,
        hints=hints,
        entity=selected_entity,
        progress_cb=_print_progress,
    )

    # Print final succinct answer
    if isinstance(out, dict):
        resp = out.get("response")
        if isinstance(resp, dict) and resp.get("text"):
            print("\nAnswer:", resp.get("text"))
        elif out.get("final"):
            print("\nAnswer:", out.get("final"))
    else:
        print("\nAnswer:", out)


def main():
    parser = argparse.ArgumentParser(description="Debug a chat session as a specific user")
    parser.add_argument("--email", type=str, help="User email")
    parser.add_argument("--role", type=str, choices=["admin", "reviewer", "executor"], help="User role")
    parser.add_argument("--question", type=str, help="Single question to ask")
    parser.add_argument("--questions_file", type=str, help="Path to file with one question per line")
    args = parser.parse_args()

    if not args.email and not args.role:
        print("Error: Provide --email or --role", file=sys.stderr)
        sys.exit(2)

    questions: List[str] = []
    if args.question:
        questions.append(args.question)
    if args.questions_file:
        try:
            with open(args.questions_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        questions.append(line)
        except Exception as e:
            print(f"Failed to read questions_file: {e}", file=sys.stderr)
            sys.exit(2)

    if not questions:
        print("Enter questions (blank line to finish):")
        while True:
            q = input("> ").strip()
            if not q:
                break
            questions.append(q)

    db = SessionLocal()
    try:
        user = find_user(db, args.email, args.role)
        for q in questions:
            run_single_question(db, user, q)
    finally:
        db.close()


if __name__ == "__main__":
    main()


