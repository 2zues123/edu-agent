from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from src.graph import LangGraphAcademicAgent, GraphAgentAnswer
from src.retriever import RetrievedChunk


EXAMPLE_QUESTIONS = [
    "机器学习课程多少学分？",
    "数字图像处理课程的考核方式是什么？",
    "2024培养方案的软件工程专业毕业要求是什么？",
    "如果挂科会影响毕业吗？",
    "人工智能导论有哪些先修课程？",
]

LEGACY_HISTORY_FILE = Path(".chat_history/history.json")
CONVERSATIONS_FILE = Path(".chat_history/conversations.json")
MAX_HISTORY_ITEMS = 20
QUICK_QUESTION_COUNT = 3


THEME_CSS = """
<style>
    :root {
        --app-bg: #ffffff;
        --panel-bg: #ffffff;
        --ink: #202123;
        --muted: #6b7280;
        --line: #e5e7eb;
        --brand: #111827;
        --brand-soft: #f3f4f6;
        --success-soft: #ecfdf3;
        --warning-soft: #fff8e6;
    }

    .stApp {
        background: var(--app-bg);
        color: var(--ink);
    }

    [data-testid="stAppViewContainer"] > .main .block-container {
        max-width: 860px;
        padding-left: 1.25rem;
        padding-right: 1.25rem;
        padding-top: 1rem;
        padding-bottom: 7.5rem;
    }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding: 14px 10px;
    }

    .sidebar-brand {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 10px;
        color: var(--ink);
        font-size: 0.96rem;
        font-weight: 700;
        overflow-wrap: anywhere;
    }

    .sidebar-brand-main {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
    }

    .sidebar-close {
        color: var(--muted);
        font-size: 1.1rem;
        font-weight: 400;
    }

    .sidebar-nav {
        border-bottom: 0;
        padding-bottom: 8px;
        margin-bottom: 10px;
    }

    .sidebar-nav-link {
        display: flex;
        align-items: center;
        gap: 10px;
        height: 38px;
        padding: 0 4px;
        border-radius: 7px;
        color: var(--ink);
        font-size: 0.9rem;
        font-weight: 500;
        text-decoration: none;
    }

    .sidebar-nav-link:hover,
    .sidebar-nav-link.active {
        background: rgba(0, 0, 0, 0.05);
        color: var(--ink);
        text-decoration: none;
    }

    .sidebar-nav-icon {
        width: 18px;
        text-align: center;
        color: var(--ink);
        font-size: 1rem;
    }

    .sidebar-section-title {
        color: var(--muted);
        font-size: 0.78rem;
        margin: 2px 0 8px;
    }

    .app-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 42px;
        margin-bottom: 18px;
    }

    .app-title {
        color: var(--ink);
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: 0;
    }

    .app-hero {
        border: 0;
        background: transparent;
        border-radius: 0;
        padding: min(11vh, 92px) 0 24px;
        margin: 0;
        box-shadow: none;
        text-align: center;
    }

    .app-hero h1 {
        color: var(--ink);
        font-size: 1.85rem;
        line-height: 1.2;
        letter-spacing: 0;
        margin: 0 0 8px 0;
    }

    .app-hero p {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.55;
        max-width: 560px;
        margin: 0 auto;
    }

    .answer-sources {
        color: var(--muted);
        font-size: 0.92rem;
        margin: 10px 0 4px;
    }

    .answer-sources a {
        color: var(--brand);
        text-decoration: none;
        font-weight: 650;
    }

    .quick-questions-label {
        color: var(--muted);
        font-size: 0.68rem;
        margin: 8px 0 5px;
    }

    .st-key-quick-question-0 button,
    .st-key-quick-question-1 button,
    .st-key-quick-question-2 button {
        min-height: 26px;
        padding: 3px 8px;
        border-radius: 999px;
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 500;
        background: #ffffff;
        box-shadow: none;
        border-color: var(--line);
    }

    .st-key-quick-question-0 button p,
    .st-key-quick-question-1 button p,
    .st-key-quick-question-2 button p {
        font-size: 0.72rem;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .source-anchor {
        scroll-margin-top: 96px;
    }

    .source-text {
        color: var(--ink);
        line-height: 1.72;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
    }

    .source-text mark {
        background: #fff1a8;
        border-radius: 4px;
        padding: 0 3px;
    }

    div[data-testid="stMetric"] {
        background: var(--panel-bg);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 8px 22px rgba(16, 24, 40, 0.045);
        overflow-wrap: anywhere;
    }

    div[data-testid="stMetricLabel"] p {
        color: var(--muted);
        font-size: 0.84rem;
    }

    div[data-testid="stMetricValue"] {
        color: var(--ink);
        font-size: 1.03rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }

    [data-testid="stChatMessage"] {
        border-radius: 0;
        border: 0;
        background: transparent;
        box-shadow: none;
        overflow-wrap: anywhere;
        padding-left: 0;
        padding-right: 0;
    }

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
        line-height: 1.72;
    }

    .stAlert {
        border-radius: 8px;
    }

    .stExpander {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel-bg);
        box-shadow: 0 8px 22px rgba(16, 24, 40, 0.035);
        overflow: hidden;
        overflow-wrap: anywhere;
    }

    .stButton > button {
        border-radius: 8px;
        border: 1px solid var(--line);
        background: #ffffff;
        min-height: 42px;
        color: var(--ink);
        transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
    }

    .stButton > button:hover {
        border-color: rgba(22, 104, 220, 0.42);
        box-shadow: 0 8px 18px rgba(22, 104, 220, 0.10);
        transform: translateY(-1px);
    }

    [data-testid="stSidebar"] [class*="st-key-history-"] {
        margin: -0.18rem 0 -0.52rem 0;
    }

    [data-testid="stSidebar"] [class*="st-key-history-"].active-conversation button {
        background: rgba(0, 0, 0, 0.05) !important;
        font-weight: 650;
    }

    [data-testid="stSidebar"] [class*="st-key-history-"] button {
        position: relative;
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        min-height: 30px;
        height: 30px;
        padding: 0 28px 0 8px;
        border: 0 !important;
        border-radius: 6px;
        background: transparent !important;
        color: var(--ink);
        box-shadow: none !important;
        text-align: left;
        transform: none !important;
    }

    [data-testid="stSidebar"] [class*="st-key-history-"] button [data-testid="stMarkdownContainer"] {
        display: block;
        width: 100%;
        min-width: 0;
        text-align: left !important;
    }

    [data-testid="stSidebar"] [class*="st-key-history-"] button::after {
        content: "";
    }

    [data-testid="stSidebar"] [class*="st-key-history-"] button:hover {
        border: 0 !important;
        background: rgba(0, 0, 0, 0.04) !important;
        box-shadow: none !important;
        transform: none !important;
        color: #000000;
    }

    [data-testid="stSidebar"] [class*="st-key-history-"] button p {
        width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.86rem;
        line-height: 30px;
        font-weight: 500;
        text-align: left !important;
    }

    [data-testid="stSidebar"] div[data-testid="stPopover"] button {
        min-height: 28px;
        height: 28px;
        width: 28px;
        padding: 0;
        border: 0 !important;
        border-radius: 999px;
        background: transparent !important;
        color: var(--muted);
        font-size: 0.86rem;
        font-weight: 500;
        box-shadow: none !important;
        transform: none !important;
    }

    [data-testid="stSidebar"] div[data-testid="stPopover"] button:hover {
        background: rgba(0, 0, 0, 0.04) !important;
        color: var(--ink);
    }

    [data-testid="stSidebar"] div[data-testid="stPopover"] button p {
        font-size: 0.86rem;
        line-height: 28px;
        white-space: nowrap;
        text-align: center;
        width: 0;
        overflow: hidden;
    }

    div[data-testid="stPopoverBody"] {
        min-width: 168px;
        border-radius: 12px !important;
        border: 1px solid rgba(229, 231, 235, 0.9) !important;
        background: rgba(255, 255, 255, 0.98) !important;
        box-shadow: 0 12px 32px rgba(15, 23, 42, 0.13) !important;
        padding: 6px !important;
    }

    div[data-testid="stPopoverBody"] .stButton > button {
        justify-content: flex-start;
        min-height: 32px;
        height: 32px;
        padding: 0 10px;
        border: 0 !important;
        border-radius: 8px;
        background: transparent !important;
        color: var(--ink);
        font-size: 0.86rem;
        font-weight: 500;
        box-shadow: none !important;
        transform: none !important;
    }

    div[data-testid="stPopoverBody"] .stButton > button:hover {
        background: rgba(0, 0, 0, 0.045) !important;
        border: 0 !important;
        box-shadow: none !important;
        transform: none !important;
    }

    div[data-testid="stPopoverBody"] .stButton > button p {
        font-size: 0.86rem;
        line-height: 32px;
        text-align: left;
    }

    div[data-testid="stPopoverBody"] [class*="st-key-delete-"] button,
    div[data-testid="stPopoverBody"] [class*="st-key-delete-confirm-"] button {
        color: #c2410c !important;
    }

    div[data-testid="stPopoverBody"] [class*="st-key-delete-"] button:hover,
    div[data-testid="stPopoverBody"] [class*="st-key-delete-confirm-"] button:hover {
        background: rgba(220, 38, 38, 0.08) !important;
    }

    [data-testid="stSidebar"] div[data-testid="column"] {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    [data-testid="stSidebar"] div[data-testid="column"] + div[data-testid="column"] {
        margin-left: -0.35rem;
    }

    .conversation-menu-note {
        color: var(--muted);
        font-size: 0.76rem;
        line-height: 1.45;
        margin: 4px 0 8px;
    }

    [data-testid="stSidebar"] .st-key-clear-chat button {
        min-height: 36px;
        height: 36px;
        border-radius: 6px;
        border-color: #d1d5db;
        color: var(--ink);
        font-size: 0.86rem;
        background: #ffffff;
        box-shadow: none;
        transform: none;
    }

    [data-testid="stSidebar"] .st-key-clear-chat button:hover {
        border-color: #c7ccd4;
        background: rgba(0, 0, 0, 0.03);
        box-shadow: none;
        transform: none;
    }

    .search-panel,
    .library-placeholder {
        padding-top: 10vh;
    }

    .search-panel h1,
    .library-placeholder h1 {
        font-size: 1.6rem;
        margin-bottom: 8px;
    }

    .search-panel p,
    .library-placeholder p {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.6;
    }

    .search-result {
        border-radius: 8px;
        padding: 10px 12px;
        margin: 8px 0;
        background: #ffffff;
        border: 1px solid var(--line);
    }

    .search-result-title {
        color: var(--ink);
        font-size: 0.92rem;
        font-weight: 650;
        margin-bottom: 4px;
    }

    .search-result-meta {
        color: var(--muted);
        font-size: 0.74rem;
        margin-bottom: 6px;
    }

    .search-result-summary {
        color: var(--ink);
        font-size: 0.84rem;
        line-height: 1.5;
    }

    .search-result mark,
    .highlight-message {
        background: #fff1a8;
        border-radius: 4px;
        padding: 0 3px;
    }

    .search-hit-banner {
        display: inline-block;
        color: #7a4b00;
        background: #fff7d6;
        border-radius: 999px;
        padding: 2px 8px;
        font-size: 0.72rem;
        margin-bottom: 6px;
    }

    div[data-testid="stChatInput"] {
        background: rgba(255, 255, 255, 0.96);
        border-top: 0;
        padding: 10px 0 14px;
    }

    div[data-testid="stChatInput"] textarea {
        border-radius: 18px;
    }

    h2, h3 {
        color: var(--ink);
        letter-spacing: 0;
    }

    @media (max-width: 760px) {
        [data-testid="stAppViewContainer"] > .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }

        .app-hero {
            padding: 7vh 0 18px;
            margin-bottom: 0;
        }

        .app-hero h1 {
            font-size: 1.35rem;
            margin-bottom: 6px;
        }

        .app-hero p {
            font-size: 0.82rem;
            line-height: 1.48;
        }

        .quick-questions-label {
            margin-top: 6px;
        }

        .st-key-quick-question-0 button,
        .st-key-quick-question-1 button,
        .st-key-quick-question-2 button {
            width: 100%;
        }

        div[data-testid="stMetric"] {
            padding: 10px 12px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 0.95rem;
        }
    }
</style>
"""


@st.cache_resource
def load_agent() -> LangGraphAcademicAgent:
    return LangGraphAcademicAgent()


def apply_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def apply_sidebar_active_style(active_panel: str, current_index: int | None) -> None:
    history_selector = f'[data-testid="stSidebar"] .st-key-history-{current_index} button,' if current_index is not None else ""
    st.markdown(
        f"""
        <style>
            {history_selector}
            .never-used-selector {{
                background: rgba(0, 0, 0, 0.05) !important;
                font-weight: 650;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def make_conversation_title(question: str) -> str:
    title = question.strip().replace("\n", " ")
    return title[:20] or "新教务对话"


def normalize_conversation(conversation: dict) -> dict:
    conversation.setdefault("id", str(uuid4()))
    conversation.setdefault("title", "未命名教务对话")
    conversation.setdefault("created_at", now_text())
    conversation.setdefault("updated_at", conversation.get("created_at") or now_text())
    conversation.setdefault("messages", [])
    conversation.setdefault("pinned", False)
    conversation.setdefault("share_id", None)
    return conversation


def load_legacy_history() -> list[dict[str, str]]:
    if not LEGACY_HISTORY_FILE.exists():
        return []
    try:
        return json.loads(LEGACY_HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def load_conversations() -> list[dict]:
    if CONVERSATIONS_FILE.exists():
        try:
            data = json.loads(CONVERSATIONS_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            return [normalize_conversation(item) for item in data if isinstance(item, dict)]
        except (json.JSONDecodeError, OSError):
            return []

    migrated = []
    for item in load_legacy_history():
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()
        created_at = item.get("created_at") or now_text()
        if not question:
            continue
        migrated.append(
            {
                "id": str(uuid4()),
                "title": make_conversation_title(question),
                "created_at": created_at,
                "updated_at": created_at,
                "pinned": False,
                "share_id": None,
                "messages": [
                    {
                        "id": str(uuid4()),
                        "role": "user",
                        "content": question,
                        "created_at": created_at,
                    },
                    {
                        "id": str(uuid4()),
                        "role": "assistant",
                        "content": answer,
                        "created_at": created_at,
                    },
                ],
            }
        )
    if migrated:
        save_conversations(migrated)
    return migrated


def save_conversations(conversations: list[dict]) -> None:
    CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalized = [normalize_conversation(conversation) for conversation in conversations]
    CONVERSATIONS_FILE.write_text(
        json.dumps(normalized[:MAX_HISTORY_ITEMS], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_history() -> None:
    if CONVERSATIONS_FILE.exists():
        CONVERSATIONS_FILE.unlink()
    if LEGACY_HISTORY_FILE.exists():
        LEGACY_HISTORY_FILE.unlink()


def create_conversation(conversations: list[dict]) -> str:
    timestamp = now_text()
    conversation_id = str(uuid4())
    conversations[:] = [conversation for conversation in conversations if conversation.get("messages")]
    conversations.insert(
        0,
        {
            "id": conversation_id,
            "title": "新教务对话",
            "created_at": timestamp,
            "updated_at": timestamp,
            "pinned": False,
            "share_id": None,
            "messages": [],
        },
    )
    save_conversations(conversations)
    return conversation_id


def get_conversation(conversations: list[dict], conversation_id: str | None) -> dict | None:
    if not conversation_id:
        return None
    for conversation in conversations:
        if conversation.get("id") == conversation_id:
            return conversation
    return None


def conversation_timestamp(conversation: dict) -> float:
    value = conversation.get("updated_at") or conversation.get("created_at") or "1970-01-01 00:00"
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return 0.0


def ensure_current_conversation(conversations: list[dict]) -> str:
    current_id = st.session_state.get("current_conversation_id")
    if get_conversation(conversations, current_id):
        return current_id
    return create_conversation(conversations)


def sorted_conversations(conversations: list[dict]) -> list[dict]:
    return sorted(
        conversations,
        key=lambda item: (
            not bool(item.get("pinned", False)),
            -conversation_timestamp(item),
        ),
    )


def visible_conversations(conversations: list[dict]) -> list[dict]:
    return [conversation for conversation in sorted_conversations(conversations) if conversation.get("messages")]


def toggle_conversation_pin(conversations: list[dict], conversation_id: str) -> None:
    conversation = get_conversation(conversations, conversation_id)
    if conversation is None:
        return
    conversation["pinned"] = not bool(conversation.get("pinned", False))
    conversation["updated_at"] = now_text()
    save_conversations(sorted_conversations(conversations))


def rename_conversation(conversations: list[dict], conversation_id: str, title: str) -> None:
    conversation = get_conversation(conversations, conversation_id)
    clean_title = title.strip()
    if conversation is None or not clean_title:
        return
    conversation["title"] = clean_title[:40]
    conversation["updated_at"] = now_text()
    save_conversations(sorted_conversations(conversations))


def ensure_share_id(conversations: list[dict], conversation_id: str) -> str | None:
    conversation = get_conversation(conversations, conversation_id)
    if conversation is None:
        return None
    if not conversation.get("share_id"):
        conversation["share_id"] = str(uuid4())[:12]
        save_conversations(sorted_conversations(conversations))
    return conversation.get("share_id")


def delete_conversation(conversations: list[dict], conversation_id: str) -> str:
    remaining = [conversation for conversation in conversations if conversation.get("id") != conversation_id]
    conversations[:] = remaining
    next_visible = visible_conversations(conversations)
    if next_visible:
        next_id = next_visible[0]["id"]
    else:
        next_id = create_conversation(conversations)
        return next_id
    save_conversations(sorted_conversations(conversations))
    return next_id


def source_to_dict(source: RetrievedChunk) -> dict:
    return {
        "chunk_id": source.chunk_id,
        "title": source.title,
        "category": source.category,
        "source_file": source.source_file,
        "heading": source.heading,
        "text": source.text,
        "score": source.score,
    }


def source_from_dict(data: dict) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=data.get("chunk_id", ""),
        title=data.get("title", ""),
        category=data.get("category", ""),
        source_file=data.get("source_file", ""),
        heading=data.get("heading", ""),
        text=data.get("text", ""),
        score=float(data.get("score", 0.0)),
    )


def result_to_dict(result: GraphAgentAnswer) -> dict:
    return {
        "question": result.question,
        "intent_name": result.intent_name,
        "intent_description": result.intent_description,
        "high_risk": result.high_risk,
        "answer": result.answer,
        "sources": [source_to_dict(source) for source in result.sources],
    }


def result_from_dict(data: dict) -> GraphAgentAnswer:
    return GraphAgentAnswer(
        question=data.get("question", ""),
        intent_name=data.get("intent_name", "general"),
        intent_description=data.get("intent_description", "通用问题"),
        high_risk=bool(data.get("high_risk", False)),
        answer=data.get("answer", ""),
        sources=[source_from_dict(source) for source in data.get("sources", [])],
    )


def stream_answer_text(text: str):
    for index in range(0, len(text), 8):
        yield text[index : index + 8]
        time.sleep(0.015)


def render_source_links(result: GraphAgentAnswer) -> None:
    if not result.sources:
        return

    links = "　".join(
        f'<a href="#source-{index}">资料{index}</a>'
        for index, _source in enumerate(result.sources, start=1)
    )
    st.markdown(
        f'<div class="answer-sources">依据：{links}</div>',
        unsafe_allow_html=True,
    )


def highlight_keyword(text: str, keyword: str) -> str:
    escaped = html.escape(text)
    if not keyword:
        return escaped
    pattern = re.compile(re.escape(html.escape(keyword)), re.IGNORECASE)
    return pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", escaped)


def build_excerpt(text: str, keyword: str, *, radius: int = 42) -> str:
    compact = " ".join(text.split())
    if not keyword:
        return compact[: radius * 2]
    index = compact.lower().find(keyword.lower())
    if index < 0:
        return compact[: radius * 2]
    start = max(0, index - radius)
    end = min(len(compact), index + len(keyword) + radius)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(compact) else ""
    return f"{prefix}{compact[start:end]}{suffix}"


def search_conversations(conversations: list[dict], keyword: str) -> list[dict]:
    keyword = keyword.strip()
    if not keyword:
        return []

    results = []
    for conversation in visible_conversations(conversations):
        title = conversation.get("title", "未命名教务对话")
        title_matched = keyword.lower() in title.lower()
        if title_matched:
            results.append(
                {
                    "conversation_id": conversation["id"],
                    "message_id": None,
                    "title": title,
                    "summary": title,
                    "created_at": conversation.get("updated_at") or conversation.get("created_at") or "",
                }
            )

        for message in conversation.get("messages", []):
            content = message.get("content", "")
            if keyword.lower() not in content.lower():
                continue
            results.append(
                {
                    "conversation_id": conversation["id"],
                    "message_id": message.get("id"),
                    "title": title,
                    "summary": build_excerpt(content, keyword),
                    "created_at": message.get("created_at") or conversation.get("updated_at") or "",
                }
            )
    return results[:30]


def highlight_source_text(text: str, heading: str) -> str:
    escaped_text = html.escape(text)
    keywords = [heading.strip()] if heading and heading != "未识别章节" else []

    section_match = re.match(r"^(\d+(?:\.\d+)*[、.．]?\s*[^：:，,。]*)", heading or "")
    if section_match:
        keywords.append(section_match.group(1).strip())

    for keyword in dict.fromkeys(item for item in keywords if item):
        escaped_keyword = html.escape(keyword)
        escaped_text = escaped_text.replace(escaped_keyword, f"<mark>{escaped_keyword}</mark>", 1)
    return escaped_text


def render_quick_questions() -> None:
    st.markdown('<div class="quick-questions-label">可以这样问</div>', unsafe_allow_html=True)
    quick_questions = EXAMPLE_QUESTIONS[:QUICK_QUESTION_COUNT]
    columns = st.columns(len(quick_questions))
    for index, question in enumerate(quick_questions):
        if columns[index].button(question, key=f"quick-question-{index}", use_container_width=True):
            st.session_state.pending_question = question


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("id") == st.session_state.get("highlight_message_id"):
            st.markdown('<div class="search-hit-banner">搜索匹配</div>', unsafe_allow_html=True)
        if message["role"] == "assistant" and "result" in message:
            render_answer(result_from_dict(message["result"]))
        else:
            st.markdown(message.get("content", ""))


def clear_search_keyword() -> None:
    st.session_state.search_keyword = ""


def first_query_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def process_sidebar_query_params(conversations: list[dict]) -> None:
    nav_action = first_query_value(st.query_params.get("nav_action"))
    panel = first_query_value(st.query_params.get("panel"))

    if nav_action == "new":
        new_id = create_conversation(conversations)
        st.session_state.current_conversation_id = new_id
        st.session_state.active_panel = "chat"
        st.session_state.pop("pending_question", None)
        st.session_state.pop("highlight_message_id", None)
        st.query_params.clear()
        st.rerun()

    if panel in {"chat", "search", "library"}:
        st.session_state.active_panel = panel
        st.query_params.clear()
        st.rerun()


def render_search_panel(conversations: list[dict]) -> None:
    st.markdown(
        """
        <section class="search-panel">
            <h1>搜索对话内容</h1>
            <p>可搜索历史会话标题、用户提问和智能回答。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    keyword_col, clear_col = st.columns([8, 1])
    with keyword_col:
        keyword = st.text_input(
            "搜索关键词",
            key="search_keyword",
            placeholder="输入课程、培养方案、成绩、流程等关键词",
            label_visibility="collapsed",
        )
    with clear_col:
        st.button(
            "清空",
            use_container_width=True,
            disabled=not bool(st.session_state.get("search_keyword")),
            on_click=clear_search_keyword,
        )

    results = search_conversations(conversations, keyword)
    st.session_state.search_results = results

    if not keyword:
        st.info("输入关键词后，将在全部历史教务对话中搜索。")
        return
    if not results:
        st.info("未找到相关教务对话")
        return

    for index, result in enumerate(results):
        st.markdown(
            f"""
            <div class="search-result">
                <div class="search-result-title">{highlight_keyword(result["title"], keyword)}</div>
                <div class="search-result-meta">{html.escape(result.get("created_at", ""))}</div>
                <div class="search-result-summary">{highlight_keyword(result["summary"], keyword)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("打开这条结果", key=f"search-result-{index}", use_container_width=True):
            st.session_state.current_conversation_id = result["conversation_id"]
            st.session_state.highlight_message_id = result.get("message_id")
            st.session_state.active_panel = "chat"
            st.rerun()


def render_library_placeholder() -> None:
    st.markdown(
        """
        <section class="library-placeholder">
            <h1>教务功能库</h1>
            <p>功能库正在建设中。后续将集中提供培养方案查询、课程信息查询、成绩与学业事务、考试事务、学籍事务和办事流程指南等能力。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_conversation_actions(conversations: list[dict], conversation: dict, index: int) -> None:
    conversation_id = conversation["id"]
    with st.popover(" ", use_container_width=True):
        if st.button("分享", key=f"share-{index}", use_container_width=True):
            share_id = ensure_share_id(conversations, conversation_id)
            st.session_state.shared_conversation_id = conversation_id
            st.session_state.shared_conversation_code = share_id

        if st.session_state.get("shared_conversation_id") == conversation_id and conversation.get("share_id"):
            st.markdown('<div class="conversation-menu-note">本地分享码</div>', unsafe_allow_html=True)
            st.code(conversation["share_id"], language=None)

        pin_label = "取消固定" if conversation.get("pinned") else "固定"
        if st.button(pin_label, key=f"pin-{index}", use_container_width=True):
            toggle_conversation_pin(conversations, conversation_id)
            st.rerun()

        if st.session_state.get("renaming_conversation_id") == conversation_id:
            new_title = st.text_input(
                "新标题",
                value=conversation.get("title", "未命名教务对话"),
                key=f"rename-input-{index}",
                label_visibility="collapsed",
            )
            save_col, cancel_col = st.columns(2)
            with save_col:
                if st.button("保存", key=f"rename-save-{index}", use_container_width=True):
                    rename_conversation(conversations, conversation_id, new_title)
                    st.session_state.pop("renaming_conversation_id", None)
                    st.rerun()
            with cancel_col:
                if st.button("取消", key=f"rename-cancel-{index}", use_container_width=True):
                    st.session_state.pop("renaming_conversation_id", None)
                    st.rerun()
        elif st.button("重命名", key=f"rename-{index}", use_container_width=True):
            st.session_state.renaming_conversation_id = conversation_id
            st.rerun()

        if st.session_state.get("delete_confirm_conversation_id") == conversation_id:
            st.warning("确认删除该对话？")
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button("确认", key=f"delete-confirm-{index}", use_container_width=True):
                    next_id = delete_conversation(conversations, conversation_id)
                    if st.session_state.get("current_conversation_id") == conversation_id:
                        st.session_state.current_conversation_id = next_id
                    st.session_state.pop("delete_confirm_conversation_id", None)
                    st.session_state.pop("highlight_message_id", None)
                    st.rerun()
            with cancel_col:
                if st.button("取消", key=f"delete-cancel-{index}", use_container_width=True):
                    st.session_state.pop("delete_confirm_conversation_id", None)
                    st.rerun()
        elif st.button("删除", key=f"delete-{index}", use_container_width=True):
            st.session_state.delete_confirm_conversation_id = conversation_id
            st.rerun()


def render_sidebar(conversations: list[dict], current_conversation_id: str) -> None:
    active_panel = st.session_state.get("active_panel", "chat")
    chat_active = " active" if active_panel == "chat" else ""
    search_active = " active" if active_panel == "search" else ""
    library_active = " active" if active_panel == "library" else ""
    st.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-brand-main">
                <span>✦</span>
                <span>高校教务教学智能体</span>
            </div>
            <span class="sidebar-close">×</span>
        </div>
        <div class="sidebar-nav">
            <a class="sidebar-nav-link{chat_active}" href="?nav_action=new" target="_self">
                <span class="sidebar-nav-icon">✎</span><span>发起新教务对话</span>
            </a>
            <a class="sidebar-nav-link{search_active}" href="?panel=search" target="_self">
                <span class="sidebar-nav-icon">⌕</span><span>搜索对话内容</span>
            </a>
            <a class="sidebar-nav-link{library_active}" href="?panel=library" target="_self">
                <span class="sidebar-nav-icon">▦</span><span>教务功能库</span>
            </a>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div><div class='sidebar-section-title'>最近⌄</div>", unsafe_allow_html=True)

    recent_conversations = visible_conversations(conversations)
    if recent_conversations:
        for index, conversation in enumerate(recent_conversations[:8]):
            title = conversation.get("title") or "未命名教务对话"
            display_title = f"📌 {title}" if conversation.get("pinned") else title
            title_col, menu_col = st.columns([0.86, 0.14], gap="small")
            with title_col:
                if st.button(display_title, key=f"history-{index}", use_container_width=True):
                    st.session_state.current_conversation_id = conversation["id"]
                    st.session_state.active_panel = "chat"
                    st.session_state.pop("pending_question", None)
                    st.session_state.pop("highlight_message_id", None)
                    st.rerun()
            with menu_col:
                render_conversation_actions(conversations, conversation, index)
    else:
        st.caption("暂无历史对话")

    if st.button("清空历史对话", key="clear-chat", use_container_width=True):
        clear_history()
        st.session_state.current_conversation_id = str(uuid4())
        st.session_state.active_panel = "chat"
        st.session_state.pop("pending_question", None)
        st.session_state.pop("highlight_message_id", None)
        st.rerun()


def render_answer(result: GraphAgentAnswer, *, stream_answer: bool = False) -> None:
    intent_label = f"{result.intent_name}｜{result.intent_description}"
    risk_label = "需人工确认" if result.high_risk else "可直接参考"

    if result.high_risk:
        st.warning("这个问题可能涉及正式教务认定，请以教务系统、学院或教务部门的最终审核结果为准。")

    st.subheader("智能回答")
    if stream_answer:
        st.write_stream(stream_answer_text(result.answer))
    else:
        st.markdown(result.answer)
    render_source_links(result)

    with st.expander("问题概况", expanded=False):
        col_intent, col_risk, col_sources = st.columns([2, 1, 1])
        col_intent.metric("问题类型", intent_label)
        col_risk.metric("参考建议", risk_label)
        if result.intent_name == "knowledge":
            col_sources.metric("回答方式", "直接回答")
        else:
            col_sources.metric("参考资料", len(result.sources))

    if result.intent_name == "knowledge":
        return

    st.subheader("参考资料")
    if not result.sources:
        st.info("暂时没有找到可展示的参考资料。")
        return

    for index, source in enumerate(result.sources, start=1):
        heading = source.heading or "未识别章节"
        st.markdown(f'<div id="source-{index}" class="source-anchor"></div>', unsafe_allow_html=True)
        with st.expander(f"{index}. {source.title}｜{heading}", expanded=False):
            st.caption(f"资料类型：{source.category} ｜ 来源文件：{source.source_file}")
            st.markdown(
                f'<div class="source-text">{highlight_source_text(source.text, heading)}</div>',
                unsafe_allow_html=True,
            )


def main() -> None:
    st.set_page_config(
        page_title="高校教务教学智能体",
        page_icon="🎓",
        layout="wide",
    )

    apply_theme()

    if "active_panel" not in st.session_state:
        st.session_state.active_panel = "chat"
    if "search_keyword" not in st.session_state:
        st.session_state.search_keyword = ""
    if "search_results" not in st.session_state:
        st.session_state.search_results = []

    conversations = load_conversations()
    process_sidebar_query_params(conversations)
    current_conversation_id = ensure_current_conversation(conversations)
    st.session_state.current_conversation_id = current_conversation_id
    current_conversation = get_conversation(conversations, current_conversation_id)
    current_messages = current_conversation.get("messages", []) if current_conversation else []

    recent = visible_conversations(conversations)
    current_index = next(
        (index for index, conversation in enumerate(recent[:8]) if conversation.get("id") == current_conversation_id),
        None,
    )
    apply_sidebar_active_style(st.session_state.active_panel, current_index)

    title_col, menu_col = st.columns([10, 1])
    with title_col:
        st.markdown('<div class="app-title">高校教务教学智能体</div>', unsafe_allow_html=True)
    with menu_col:
        with st.popover("⋯", use_container_width=True):
            st.caption("更多设置")
            use_llm = st.toggle("生成完整回答", value=True)
            top_k = st.slider("参考资料范围", min_value=1, max_value=10, value=5)

    if st.session_state.active_panel == "search":
        with st.sidebar:
            render_sidebar(conversations, current_conversation_id)
        render_search_panel(conversations)
        return

    if st.session_state.active_panel == "library":
        with st.sidebar:
            render_sidebar(conversations, current_conversation_id)
        render_library_placeholder()
        return

    if not current_messages:
        st.markdown(
            """
            <section class="app-hero">
                <h1>学生教务问答助手</h1>
                <p>输入培养方案、课程大纲、成绩事务或办事流程相关问题，系统会结合校内资料给出回答，并列出可参考的原文依据。</p>
            </section>
            """,
            unsafe_allow_html=True,
        )

    with st.sidebar:
        render_sidebar(conversations, current_conversation_id)

    for message in current_messages:
        render_message(message)

    render_quick_questions()

    typed_question = st.chat_input("请输入你的教务或课程问题")
    question = st.session_state.pop("pending_question", None) or typed_question
    if not question:
        return

    user_message = {
        "id": str(uuid4()),
        "role": "user",
        "content": question,
        "created_at": now_text(),
    }
    current_messages.append(user_message)
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("正在识别意图、检索知识库并生成回答..."):
            try:
                result = load_agent().answer(question, top_k=top_k, use_llm=use_llm)
            except Exception as exc:
                st.error(f"运行失败：{exc}")
                current_messages.append(
                    {
                        "id": str(uuid4()),
                        "role": "assistant",
                        "content": f"运行失败：{exc}",
                        "created_at": now_text(),
                    }
                )
                if current_conversation is not None:
                    current_conversation["messages"] = current_messages
                    current_conversation["updated_at"] = now_text()
                    save_conversations(sorted_conversations(conversations))
                return
        render_answer(result, stream_answer=True)

    if current_conversation is not None:
        if len(current_messages) == 1:
            current_conversation["title"] = make_conversation_title(question)
        current_conversation["messages"] = current_messages
        current_conversation["updated_at"] = now_text()
    current_messages.append(
        {
            "id": str(uuid4()),
            "role": "assistant",
            "content": result.answer,
            "created_at": now_text(),
            "result": result_to_dict(result),
        }
    )
    if current_conversation is not None:
        current_conversation["messages"] = current_messages
        current_conversation["updated_at"] = now_text()
    save_conversations(sorted_conversations(conversations))


if __name__ == "__main__":
    main()
