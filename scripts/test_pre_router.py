from __future__ import annotations

from src.app.chat.brain.pre_router import classify


SAMPLES = [
    "Show my tasks in progress",
    "List the task updates from executors which have blockers and risks this week",
    "Give me a portfolio overview",
    "EO details 123e4567-e89b-12d3-a456-426614174000",
    "Anything on accounting I should be looking at?",
    "How many overdue tasks do we have?",
    "Trend of updates per week for last 7 days",
    "Show PMO assignments for this EO 11111111-1111-1111-1111-111111111111",
    "Top executors by updates this month",
    "Find users named kevin",
]


def run():
    for q in SAMPLES:
        res = classify(q)
        print("--")
        print("Q:", q)
        print("→", res)


if __name__ == "__main__":
    run()


