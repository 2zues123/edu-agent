"""LangGraph node functions for the academic affairs Agent."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from src.intent import classify_intent
from src.llm import build_deepseek_chat
from src.prompts import KNOWLEDGE_SYSTEM_PROMPT, SYSTEM_PROMPT, build_knowledge_prompt, build_user_prompt
from src.retriever import HybridRetriever, RetrievedChunk
from src.risk import RISK_NOTICE, is_high_risk
from src.state import AgentState


def classify_intent_node(state: AgentState) -> AgentState:
    return {"intent": classify_intent(state["question"])}


def detect_risk_node(state: AgentState) -> AgentState:
    high_risk = is_high_risk(state["question"])
    return {
        "high_risk": high_risk,
        "risk_notice": RISK_NOTICE if high_risk else None,
    }


def retrieve_knowledge_node(state: AgentState) -> AgentState:
    intent = state.get("intent")
    if intent and intent.name == "knowledge":
        return {"sources": []}

    retriever = HybridRetriever()
    category = intent.category if intent else None
    top_k = state.get("top_k", 5)

    sources = retriever.search(state["question"], category=category, top_k=top_k)
    if not sources and category is not None:
        sources = retriever.search(state["question"], category=None, top_k=top_k)
    return {"sources": sources}


def generate_answer_node(state: AgentState) -> AgentState:
    sources = state.get("sources", [])
    risk_notice = state.get("risk_notice")
    intent = state.get("intent")

    if intent and intent.name == "knowledge":
        llm = build_deepseek_chat()
        response = llm.invoke(
            [
                SystemMessage(content=KNOWLEDGE_SYSTEM_PROMPT),
                HumanMessage(content=build_knowledge_prompt(state["question"])),
            ]
        )
        return {"answer": str(response.content)}

    if not state.get("use_llm", True):
        return {"answer": build_fallback_answer(sources, risk_notice)}

    prompt = build_user_prompt(state["question"], sources, risk_notice)
    llm = build_deepseek_chat()
    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )
    return {"answer": str(response.content)}


def build_fallback_answer(
    sources: list[RetrievedChunk],
    risk_notice: str | None,
) -> str:
    if not sources:
        return "当前知识库中没有检索到明确依据，建议咨询学院教务办公室。"

    lines = ["已检索到以下相关依据，可用于生成回答："]
    if risk_notice:
        lines.append(f"\n风险提示：{risk_notice}")
    for index, source in enumerate(sources, start=1):
        excerpt = source.text[:280].replace("\n", " ")
        lines.append(
            f"\n[资料{index}] {source.title}｜{source.heading or '未识别章节'}\n"
            f"来源：{source.source_file}\n"
            f"片段：{excerpt}"
        )
    return "\n".join(lines)
