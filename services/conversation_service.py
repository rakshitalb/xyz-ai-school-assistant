"""
Lightweight in-memory conversation history so XYZ AI can maintain context
and support follow-up questions, per the assessment's chat requirements.

This is intentionally simple (process-local dict, bounded deque) since the
assessment's mock-API style architecture doesn't call for a real database
here. If persistent, multi-instance history is needed later, this module
is the single place to swap in a real store without touching the routes.
"""

from __future__ import annotations

from collections import defaultdict, deque

_MAX_TURNS = 6

_conversations: dict[str, deque] = defaultdict(lambda: deque(maxlen=_MAX_TURNS))


def _session_key(role: str, student_name: str | None) -> str:
    return f"{role}:{(student_name or 'anonymous').strip().lower()}"


def get_history(role: str, student_name: str | None) -> list[dict]:
    key = _session_key(role, student_name)
    return list(_conversations[key])


def add_turn(role: str, student_name: str | None, question: str, answer: str) -> None:
    key = _session_key(role, student_name)
    _conversations[key].append({"question": question, "answer": answer})


def reset_history(role: str, student_name: str | None) -> None:
    key = _session_key(role, student_name)
    _conversations.pop(key, None)
