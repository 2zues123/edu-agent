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
        return {"answer": build_fallback_answer(sources, risk_notice, state["question"])}

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
    question: str = "",
) -> str:
    if not sources:
        return "当前知识库中没有检索到明确依据，建议咨询学院教务办公室。"

    if is_open_listing_question(question):
        lines = ["根据已检索资料，可参考的相关项目/成果包括："]
    else:
        lines = ["已检索到以下相关依据，可用于生成回答："]
    if risk_notice:
        lines.append(f"\n风险提示：{risk_notice}")
    for index, source in enumerate(sources, start=1):
        text = source_attr(source, "text")
        title = source_attr(source, "title") or "未命名资料"
        heading = source_attr(source, "heading") or "未识别章节"
        source_file = source_attr(source, "source_file") or "未知来源"
        excerpt = relevant_excerpt(text, question)
        source_line = f"来源：{source_file}"
        source_url = source_attr(source, "source_url")
        if source_url:
            source_line += f"\n官网链接：{source_url}"
        lines.append(
            f"\n[资料{index}] {title}｜{heading}\n"
            f"{source_line}\n"
            f"片段：{excerpt}"
        )
    return "\n".join(lines)


def is_open_listing_question(question: str) -> bool:
    return any(word in question for word in ["优秀", "项目", "成果", "荣誉", "竞赛", "大赛", "实训", "实践"])


def relevant_excerpt(text: str, question: str, *, length: int = 360) -> str:
    compact = " ".join(text.split())
    keywords = ["项目", "成果", "荣誉", "竞赛", "大赛", "实训", "实践", "AI+PBL", "创新"]
    if question:
        keywords = [word for word in keywords if word in question or word in compact] or keywords
    positions = [compact.find(word) for word in keywords if compact.find(word) >= 0]
    if not positions:
        return compact[:length]
    start = max(0, min(positions) - 80)
    end = min(len(compact), start + length)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(compact) else ""
    return f"{prefix}{compact[start:end]}{suffix}"


def source_attr(source: RetrievedChunk, name: str, default: str = "") -> str:
    value = getattr(source, name, default)
    return default if value is None else str(value)
