"""LangGraph state definitions."""

from __future__ import annotations

from typing import TypedDict

from src.intent import Intent
from src.retriever import RetrievedChunk


class AgentState(TypedDict, total=False):
    question: str
    top_k: int
    use_llm: bool
    intent: Intent
    high_risk: bool
    risk_notice: str | None
    sources: list[RetrievedChunk]
    answer: str

