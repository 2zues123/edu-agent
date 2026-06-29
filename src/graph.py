"""LangGraph workflow for the academic affairs teaching Agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from src.state import AgentState

if TYPE_CHECKING:
    from src.retriever import RetrievedChunk


@dataclass(frozen=True)
class GraphAgentAnswer:
    question: str
    intent_name: str
    intent_description: str
    answer_mode_name: str
    answer_mode_label: str
    answer_mode_description: str
    high_risk: bool
    answer: str
    sources: list[RetrievedChunk]


def build_agent_graph():
    from src.nodes import classify_intent_node, detect_risk_node, generate_answer_node, retrieve_knowledge_node

    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("detect_risk", detect_risk_node)
    graph.add_node("retrieve_knowledge", retrieve_knowledge_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "detect_risk")
    graph.add_edge("detect_risk", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "generate_answer")
    graph.add_edge("generate_answer", END)
    return graph.compile()


class LangGraphAcademicAgent:
    def __init__(self):
        self.graph = build_agent_graph()

    def answer(
        self,
        question: str,
        *,
        top_k: int = 5,
        use_llm: bool = True,
        chat_history: list[dict[str, str]] | None = None,
    ) -> GraphAgentAnswer:
        state = self.graph.invoke(
            {
                "question": question,
                "top_k": top_k,
                "use_llm": use_llm,
                "chat_history": chat_history or [],
            }
        )
        intent = state["intent"]
        mode = state.get("answer_mode")
        return GraphAgentAnswer(
            question=state["question"],
            intent_name=intent.name,
            intent_description=intent.description,
            answer_mode_name=getattr(mode, "name", "general_llm"),
            answer_mode_label=getattr(mode, "label", "通用智能问答"),
            answer_mode_description=getattr(mode, "description", ""),
            high_risk=state.get("high_risk", False),
            answer=state.get("answer", ""),
            sources=state.get("sources", []),
        )
