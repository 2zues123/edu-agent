"""LangGraph state definitions."""

from __future__ import annotations

from typing import TypedDict

from src.intent import Intent
from src.modes import AnswerMode


class AgentState(TypedDict, total=False):
    question: str
    top_k: int
    use_llm: bool
    intent: Intent
    answer_mode: AnswerMode
    high_risk: bool
    risk_notice: str | None
    sources: list[object]
    answer: str
