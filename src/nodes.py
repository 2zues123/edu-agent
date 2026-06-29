"""LangGraph node functions for the academic affairs Agent."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from src.intent import classify_intent
from src.llm import build_deepseek_chat
from src.modes import AnswerMode, GENERAL_MODE, HYBRID_MODE, STRICT_MODE, classify_answer_mode
from src.prompts import (
    GENERAL_SYSTEM_PROMPT,
    HYBRID_SYSTEM_PROMPT,
    STRICT_SYSTEM_PROMPT,
    build_general_prompt,
    build_hybrid_prompt,
    build_strict_prompt,
)
from src.retriever import HybridRetriever, RetrievedChunk
from src.risk import RISK_NOTICE, is_high_risk
from src.state import AgentState
from src.course_db import is_counting_query, query_course_db, lookup_course_info, CourseDB
from src.student_memory import build_student_profile, profile_to_llm_context

# Module-level cache — BGE model is heavy, reuse across queries
_RETRIEVER_CACHE: HybridRetriever | None = None


def _get_retriever() -> HybridRetriever:
    global _RETRIEVER_CACHE
    if _RETRIEVER_CACHE is None:
        _RETRIEVER_CACHE = HybridRetriever()
    return _RETRIEVER_CACHE


def classify_intent_node(state: AgentState) -> AgentState:
    intent = classify_intent(state["question"])
    mode = classify_answer_mode(state["question"], intent)
    return {"intent": intent, "answer_mode": mode}


def detect_risk_node(state: AgentState) -> AgentState:
    high_risk = is_high_risk(state["question"])
    return {
        "high_risk": high_risk,
        "risk_notice": RISK_NOTICE if high_risk else None,
    }


def retrieve_knowledge_node(state: AgentState) -> AgentState:
    mode = get_mode(state)
    if not mode.use_retrieval:
        return {"sources": []}

    intent = state.get("intent")
    retriever = _get_retriever()
    top_k = state.get("top_k", 5)
    question = state["question"]

    # Search all categories — RRF ranking handles relevance.
    sources = retriever.search(question, category=None, top_k=top_k)

    # ── Augment with structured course DB for counting / specific lookups ──
    sources = _augment_with_course_db(question, sources)

    return {"sources": sources}


def _augment_with_course_db(
    question: str, sources: list[RetrievedChunk]
) -> list[RetrievedChunk]:
    """Add structured course DB results for counting/listing/course-info queries."""
    # 1. Counting / listing queries (e.g. "几门数学课")
    if is_counting_query(question):
        answer = query_course_db(question)
        if answer:
            # Create a synthetic chunk with the structured answer
            fake_chunk = RetrievedChunk(
                chunk_id="course_db_count",
                title="软件工程专业培养方案（课程数据库）",
                category="programs",
                source_file="data/processed/learning_map.json",
                heading="课程统计",
                text=answer,
                score=100.0,  # highest priority
                source_url="",
                site="",
                published_at="",
            )
            # Only keep top 1-2 relevant supplementary sources (programs/courses only)
            filtered = [s for s in sources if s.category in ("programs", "courses")]
            return [fake_chunk] + filtered[:1]

    # 2. Specific course info lookup
    # Check if question asks about a known course's credits/hours/etc.
    db = CourseDB()
    course_formal_q = any(kw in question for kw in
        ["学分", "学时", "必修", "选修", "考核", "先修", "第几学期"])
    if course_formal_q:
        for course in db.courses:
            name = course.get("name", "")
            if len(name) >= 3 and name in question:
                info = lookup_course_info(name)
                if info:
                    src_file = course.get("source", "data/processed/learning_map.json")
                    fake_chunk = RetrievedChunk(
                        chunk_id=f"course_db_{course.get('code', '')}",
                        title=f"{name}（课程数据库）",
                        category="courses",
                        source_file=src_file,
                        heading="课程信息",
                        text=info,
                        score=95.0,
                        source_url="",
                        site="",
                        published_at="",
                    )
                    # Insert at position 1 (before other results), filter noise
                    sources.insert(0, fake_chunk)
                    sources = [s for s in sources if s.category in ("programs", "courses")][:2]
                    break

    return sources


def generate_answer_node(state: AgentState) -> AgentState:
    mode = get_mode(state)
    sources = state.get("sources", [])
    risk_notice = state.get("risk_notice")
    question = state["question"]
    history = state.get("chat_history") or []

    # Inject student memory context so the LLM can personalize answers
    try:
        student_ctx = profile_to_llm_context(build_student_profile())
    except Exception:
        student_ctx = ""

    if not state.get("use_llm", True):
        return {"answer": build_fallback_answer(mode, sources, risk_notice, question)}

    if mode.name == GENERAL_MODE.name:
        return {"answer": invoke_llm(GENERAL_SYSTEM_PROMPT,
                                      student_ctx + build_general_prompt(question, history=history))}

    if mode.name == STRICT_MODE.name:
        if not sources:
            # No校内资料 found — fall back to hybrid mode so the LLM
            # can still give a helpful answer while being transparent about
            # the lack of official sources.
            return {
                "answer": invoke_llm(
                    HYBRID_SYSTEM_PROMPT,
                    student_ctx + build_hybrid_prompt(question, sources, risk_notice, history=history),
                )
            }
        return {
            "answer": invoke_llm(
                STRICT_SYSTEM_PROMPT,
                student_ctx + build_strict_prompt(question, sources, risk_notice, history=history),
            )
        }

    if mode.name == HYBRID_MODE.name:
        return {
            "answer": invoke_llm(
                HYBRID_SYSTEM_PROMPT,
                student_ctx + build_hybrid_prompt(question, sources, risk_notice, history=history),
            )
        }

    return {"answer": invoke_llm(GENERAL_SYSTEM_PROMPT,
                                  student_ctx + build_general_prompt(question, history=history))}


def invoke_llm(system_prompt: str, user_prompt: str) -> str:
    llm = build_deepseek_chat()
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return str(response.content)


def get_mode(state: AgentState) -> AnswerMode:
    mode = state.get("answer_mode")
    return mode if isinstance(mode, AnswerMode) else GENERAL_MODE


def insufficient_evidence_answer(risk_notice: str | None = None) -> str:
    lines = [
        "当前资料依据不足，无法仅凭校内知识库确认这个问题的正式答案。",
        "",
        "建议：请补充更具体的专业、年级、课程名称或办理事项，或以教务系统、学院教务办公室发布的正式信息为准。",
    ]
    if risk_notice:
        lines.insert(1, f"风险提示：{risk_notice}")
    return "\n".join(lines)


def build_fallback_answer(
    mode: AnswerMode,
    sources: list[RetrievedChunk],
    risk_notice: str | None,
    question: str = "",
) -> str:
    if mode.name == GENERAL_MODE.name:
        return "当前未启用大模型，因此无法生成通用智能回答。请开启 LLM 后再提问。"

    if mode.name == STRICT_MODE.name and not sources:
        return insufficient_evidence_answer(risk_notice)

    if mode.name == HYBRID_MODE.name:
        lines = ["资料依据："]
        if sources:
            lines.extend(format_source_lines(sources, question))
        else:
            lines.append("当前资料依据不足，未检索到能直接支撑该问题的校内资料。")
        lines.extend(
            [
                "",
                "建议：",
                "当前未启用大模型，只能展示已检索资料。开启 LLM 后可结合资料生成更完整的规划建议。",
            ]
        )
        return "\n".join(lines)

    lines = ["已检索到以下校内资料依据，可用于回答："]
    if risk_notice:
        lines.append(f"\n风险提示：{risk_notice}")
    lines.extend(format_source_lines(sources, question))
    return "\n".join(lines)


def format_source_lines(sources: list[RetrievedChunk], question: str) -> list[str]:
    lines: list[str] = []
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
            f"\n[资料{index}] {title} - {heading}\n"
            f"{source_line}\n"
            f"片段：{excerpt}"
        )
    return lines


def relevant_excerpt(text: str, question: str, *, length: int = 360) -> str:
    compact = " ".join(text.split())
    keywords = [
        "培养方案", "课程", "学分", "毕业", "考试", "成绩", "补考", "重修",
        "流程", "申请", "政策", "规定", "项目", "成果", "实践",
    ]
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
