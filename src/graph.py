"""LangGraph workflow for the academic affairs teaching Agent."""

from __future__ import annotations

from dataclasses import dataclass

from langgraph.graph import END, StateGraph

from src.nodes import classify_intent_node, detect_risk_node, generate_answer_node, retrieve_knowledge_node
from src.retriever import RetrievedChunk
from src.state import AgentState


@dataclass(frozen=True)
class GraphAgentAnswer:
    question: str
    intent_name: str
    intent_description: str
    high_risk: bool
    answer: str
    sources: list[RetrievedChunk]


def build_agent_graph():
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

    def answer(self, question: str, *, top_k: int = 5, use_llm: bool = True) -> GraphAgentAnswer:
        state = self.graph.invoke(
            {
                "question": question,
                "top_k": top_k,
                "use_llm": use_llm,
            }
        )
        intent = state["intent"]
        return GraphAgentAnswer(
            question=state["question"],
            intent_name=intent.name,
            intent_description=intent.description,
            high_risk=state.get("high_risk", False),
            answer=state.get("answer", ""),
            sources=state.get("sources", []),
        )
