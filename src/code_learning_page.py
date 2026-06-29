"""Code Learning AI page — text Q&A + image-based code recognition."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from src.code_agent import (
    CodeLearningAgent,
    EXT_TO_MIME,
    validate_image_upload,
)
from src.learner_profile import update_profile_from_signal
from src.ui.design_system import apply_design_system, inject_extra_css
from src.ui.layout import render_top_nav

# Module-level agent cache — avoid recreating OpenAI clients each call
_CODE_AGENT_CACHE: CodeLearningAgent | None = None


def _get_agent() -> CodeLearningAgent:
    global _CODE_AGENT_CACHE
    if _CODE_AGENT_CACHE is None:
        _CODE_AGENT_CACHE = CodeLearningAgent()
    return _CODE_AGENT_CACHE


# ── Constants ───────────────────────────────────────────────

CODE_CONVERSATIONS_FILE = Path(".chat_history/code_conversations.json")
MAX_HISTORY_ITEMS = 20

EXAMPLE_QUESTIONS = (
    "解释这段 Python 代码的时间复杂度",
    "这段代码为什么报 IndexError？",
    "用动态规划解最长公共子序列",
    "分析这段 Java 代码的设计模式",
)

STARTER_CARDS = (
    ("代码讲解", "green", "逐行解释代码逻辑", "帮我解释这段代码：\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1"),
    ("静态 Debug", "amber", "分析报错给出修复建议", "这段代码报 TypeError: unsupported operand type(s) for +: 'int' and 'str'，帮我看看哪里有问题：\nx = 10\ny = '20'\nresult = x + y"),
    ("算法题", "blue", "思路、复杂度与参考实现", "用动态规划解「最长回文子串」，分析时间复杂度和空间复杂度"),
    ("上传截图", "rose", "上传代码截图开始学习", ""),
)

CODE_PAGE_CSS = """
/* ── User message bubble (plain text) ── */
.ds-user-bubble {
    width: fit-content;
    max-width: 100%;
    margin: 0.72rem 0 0.72rem auto;
    padding: 16px 20px;
    border-radius: 22px 22px 6px 22px;
    border: 1px solid rgba(22, 140, 140, 0.26);
    background: #DDEAE2;
    color: #17324A;
    font-weight: 650;
    line-height: 1.72;
    box-shadow: 0 16px 34px rgba(22, 140, 140, 0.10);
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}

/* ── User message bubble (with code screenshot) ── */
.ds-code-user-bubble {
    width: fit-content;
    max-width: 92%;
    margin: 0.72rem 0 0.72rem auto;
    padding: 16px 20px;
    border-radius: 22px 22px 6px 22px;
    border: 1px solid rgba(22, 140, 140, 0.26);
    background: #DDEAE2;
    color: #17324A;
    font-weight: 650;
    line-height: 1.72;
    box-shadow: 0 16px 34px rgba(22, 140, 140, 0.10);
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}
.ds-code-user-bubble pre {
    background: rgba(23, 50, 74, 0.06);
    border-radius: 10px;
    padding: 12px 16px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 0.84rem;
    line-height: 1.55;
    white-space: pre-wrap;
    overflow-x: auto;
}

/* ── Chat messages width constraints ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    width: fit-content !important;
    min-width: min(280px, 92%) !important;
    max-width: 72% !important;
    margin-left: auto !important;
    margin-right: 0 !important;
    background: #DDEAE2 !important;
    border-color: rgba(22, 140, 140, 0.26) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    width: fit-content !important;
    max-width: 86% !important;
    margin-left: 0 !important;
    margin-right: auto !important;
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    text-align: left !important;
}

/* ── Loading animation ── */
.ds-loading-bubble {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    color: #5D7183;
    font-weight: 650;
}
.ds-loading-dots {
    display: inline-flex;
    gap: 4px;
}
.ds-loading-dots span {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: #168C8C;
    opacity: 0.35;
    animation: ds-dot-pulse 1.2s ease-in-out infinite;
}
.ds-loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.ds-loading-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes ds-dot-pulse {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.35; }
    40% { transform: translateY(-4px); opacity: 1; }
}

/* ── Info banner ── */
.ds-code-info {
    background: rgba(221, 234, 226, 0.5);
    border: 1px solid rgba(22, 140, 140, 0.18);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 16px;
    color: #17324A;
    font-size: 0.85rem;
    line-height: 1.6;
}

/* Keep the code chat input to a single visual frame. */
div[data-testid="stChatInput"] {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}
div[data-testid="stChatInput"] > div {
    border: 1px solid rgba(22, 140, 140, 0.34) !important;
    border-radius: 999px !important;
    background: #FFF9EF !important;
    box-shadow: 0 14px 34px rgba(23, 50, 74, 0.10) !important;
    outline: none !important;
    overflow: hidden !important;
}
div[data-testid="stChatInput"] > div *,
div[data-testid="stChatInput"] [data-baseweb="textarea"],
div[data-testid="stChatInput"] [data-baseweb="base-input"],
div[data-testid="stChatInput"] [data-baseweb="base-input"] > div {
    background: transparent !important;
    background-color: transparent !important;
}
div[data-testid="stChatInput"] > div:focus-within {
    border-color: #168C8C !important;
    box-shadow:
        0 0 0 3px rgba(22, 140, 140, 0.14),
        0 14px 34px rgba(23, 50, 74, 0.10) !important;
}
div[data-testid="stChatInput"] textarea,
div[data-testid="stChatInput"] textarea:focus {
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;
}

@media (max-width: 760px) {
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        max-width: 94% !important;
    }
}
"""


# ── Helpers ─────────────────────────────────────────────────

def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def make_conversation_title(question: str) -> str:
    title = question.strip().replace("\n", " ").replace("\r", "")
    if len(title) > 40:
        title = title[:40] + "..."
    return title


def normalize_conversation(conv: dict) -> dict:
    conv.setdefault("id", str(uuid4()))
    conv.setdefault("messages", [])
    conv.setdefault("created_at", now_text())
    conv.setdefault("updated_at", conv.get("created_at", now_text()))
    conv.setdefault("title", "未命名代码对话")
    conv.setdefault("pinned", False)
    return conv


# ── Persistence ─────────────────────────────────────────────

def load_code_conversations() -> list[dict]:
    if not CODE_CONVERSATIONS_FILE.exists():
        return []
    try:
        data = json.loads(CODE_CONVERSATIONS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [normalize_conversation(item) for item in data if isinstance(item, dict)]


def save_code_conversations(conversations: list[dict]) -> None:
    CODE_CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalized = list(conversations)
    if len(normalized) > MAX_HISTORY_ITEMS:
        normalized = normalized[-MAX_HISTORY_ITEMS:]
    CODE_CONVERSATIONS_FILE.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_conversation(conversations: list[dict], cid: str | None) -> dict | None:
    if not cid:
        return None
    for c in conversations:
        if c.get("id") == cid:
            return c
    return None


def conversation_timestamp(conversation: dict) -> float:
    value = conversation.get("updated_at") or conversation.get("created_at") or ""
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return 0.0


def visible_conversations(conversations: list[dict]) -> list[dict]:
    return sorted(
        conversations,
        key=lambda i: (bool(i.get("pinned")), conversation_timestamp(i)),
        reverse=True,
    )


def create_conversation(conversations: list[dict]) -> str:
    timestamp = now_text()
    cid = str(uuid4())
    conversations.insert(0, {
        "id": cid, "title": "新建代码对话",
        "created_at": timestamp, "updated_at": timestamp,
        "messages": [], "pinned": False,
    })
    save_code_conversations(conversations)
    return cid


def delete_conversation(conversations: list[dict], cid: str) -> str:
    remaining = [i for i in conversations if i.get("id") != cid]
    conversations.clear()
    conversations.extend(remaining)
    v = visible_conversations(conversations)
    new_id = v[0].get("id", "") if v else ""
    save_code_conversations(conversations)
    return new_id


def toggle_conversation_pin(conversations: list[dict], cid: str) -> None:
    c = get_conversation(conversations, cid)
    if c is not None:
        c["pinned"] = not bool(c.get("pinned"))
        c["updated_at"] = now_text()
        save_code_conversations(conversations)


def rename_conversation(conversations: list[dict], cid: str, title: str) -> None:
    c = get_conversation(conversations, cid)
    if c is not None:
        t = title.strip()
        if t:
            c["title"] = t
            c["updated_at"] = now_text()
            save_code_conversations(conversations)


def clear_history() -> None:
    if CODE_CONVERSATIONS_FILE.exists():
        CODE_CONVERSATIONS_FILE.unlink()


def ensure_current_conversation(conversations: list[dict]) -> str:
    cid = st.session_state.get("code_current_id", "")
    c = get_conversation(conversations, cid if cid else None)
    if c is not None:
        return cid
    st.session_state["code_current_id"] = ""
    return ""


# ── UI Rendering ────────────────────────────────────────────

def render_starter_dashboard(conversations: list[dict]) -> None:
    """Render the welcome dashboard when no conversation is active."""
    st.markdown(
        """
        <section class="ds-hero">
            <div class="ds-hero-eyebrow">Software College · Code Learning</div>
            <h1>代码学习 AI</h1>
            <p>支持代码讲解、算法分析、静态 Debug 和图片识别代码。
            不运行代码，专注静态分析与学习辅导。</p>
            <div class="ds-hero-badges">
                <span class="ds-badge ds-badge-success">代码讲解</span>
                <span class="ds-badge ds-badge-muted">静态 Debug</span>
                <span class="ds-badge ds-badge-muted">算法分析</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.caption("选择一个场景快速开始，或直接在下方输入你的代码问题")

    card_cols = st.columns(4)
    for idx, (col, card) in enumerate(zip(card_cols, STARTER_CARDS)):
        label, accent, desc, question = card
        with col:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.caption(desc)
                if st.button("开始提问 ->", key=f"code_starter_{idx}", use_container_width=True):
                    st.session_state["code_current_id"] = ""
                    if question:
                        st.session_state["code_pending_question"] = question
                    else:
                        st.session_state["code_show_upload"] = True
                    st.rerun()


def render_conversation_actions(conversations: list[dict], conversation: dict) -> None:
    cid = str(conversation.get("id", ""))
    with st.popover("...", use_container_width=True):
        pin_label = "取消置顶" if conversation.get("pinned") else "置顶对话"
        if st.button(pin_label, key=f"code_pin_{cid}", use_container_width=True):
            toggle_conversation_pin(conversations, cid)
            st.rerun()
        if st.button("重命名", key=f"code_rn_btn_{cid}", use_container_width=True):
            st.session_state["code_renaming_id"] = cid
        if st.session_state.get("code_renaming_id") == cid:
            nt = st.text_input(
                "新标题", value=str(conversation.get("title", "")),
                key=f"code_rn_inp_{cid}", label_visibility="collapsed",
            )
            sc, cc = st.columns(2)
            with sc:
                if st.button("保存", key=f"code_rn_sv_{cid}", use_container_width=True):
                    rename_conversation(conversations, cid, nt)
                    st.session_state.pop("code_renaming_id", None)
                    st.rerun()
            with cc:
                if st.button("取消", key=f"code_rn_ccl_{cid}", use_container_width=True):
                    st.session_state.pop("code_renaming_id", None)
                    st.rerun()
        if st.button("删除对话", key=f"code_del_btn_{cid}", use_container_width=True):
            st.session_state["code_delete_id"] = cid
        if st.session_state.get("code_delete_id") == cid:
            st.warning("确定删除此对话？")
            dc, ca = st.columns(2)
            with dc:
                if st.button("确定", key=f"code_del_cfm_{cid}", use_container_width=True):
                    nid = delete_conversation(conversations, cid)
                    st.session_state["code_current_id"] = nid
                    st.session_state.pop("code_delete_id", None)
                    st.rerun()
            with ca:
                if st.button("取消", key=f"code_del_ccl_{cid}", use_container_width=True):
                    st.session_state.pop("code_delete_id", None)
                    st.rerun()


def render_sidebar(conversations: list[dict], current_id: str) -> None:
    st.markdown("#### 代码学习 AI")

    if st.button("+ 新建对话", key="code_new_conv", use_container_width=True):
        st.session_state["code_current_id"] = ""
        st.session_state["code_pending_question"] = None
        st.rerun()

    st.caption("代码讲解 | 静态 Debug | 算法分析")

    st.markdown("---")

    recent = visible_conversations(conversations)[:MAX_HISTORY_ITEMS]
    if recent:
        st.caption("历史对话")

    for i, c in enumerate(recent):
        cid = str(c.get("id", ""))
        ct = str(c.get("title") or "未命名代码对话")
        pinned = c.get("pinned")
        display = f"[置顶] {ct}" if pinned else ct

        tc, mc = st.columns([0.84, 0.16])
        with tc:
            bt = "primary" if cid == current_id else "secondary"
            if st.button(display, key=f"code_hist_{i}", use_container_width=True, type=bt):
                st.session_state["code_current_id"] = cid
                st.rerun()
        with mc:
            render_conversation_actions(conversations, c)

    if recent:
        if st.button("清空历史", key="code_clr_hist", use_container_width=True):
            clear_history()
            st.session_state["code_current_id"] = ""
            st.rerun()


def render_quick_questions() -> None:
    st.caption("试试这些问题")
    cols = st.columns(4)
    for i, q in enumerate(EXAMPLE_QUESTIONS[:4]):
        with cols[i]:
            if st.button(q, key=f"code_qq_{i}", use_container_width=True):
                st.session_state["code_pending_question"] = q
                st.rerun()


def render_learning_signal(msg: dict) -> None:
    topics = [str(item) for item in msg.get("topics", []) if item]
    courses = [str(item) for item in msg.get("related_courses", []) if item]
    difficulty = str(msg.get("difficulty") or "")
    exercises = [str(item) for item in msg.get("next_exercises", []) if item]

    chips = []
    if difficulty:
        chips.append(f"难度：{difficulty}")
    if topics:
        chips.append("知识点：" + "、".join(topics[:3]))
    if courses:
        chips.append("关联课程：" + "、".join(courses[:2]))
    if chips:
        st.caption(" | ".join(chips))

    if exercises:
        with st.expander("下一步练习", expanded=False):
            for item in exercises[:4]:
                st.markdown(f"- {item}")


def render_message(msg: dict) -> None:
    role = msg.get("role", "user")
    content = str(msg.get("content", ""))

    if role == "user":
        had_image = msg.get("has_image", False)
        _spacer, bubble = st.columns([0.34, 0.66])
        with bubble:
            if had_image:
                recognized = msg.get("recognized_code", "")
                if recognized:
                    st.markdown(
                        f'<div class="ds-code-user-bubble">'
                        f'<em>已识别截图中的代码</em>'
                        f'<pre>{html.escape(recognized)}</pre>'
                        f'{html.escape(content)}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="ds-user-bubble">{html.escape(content)}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f'<div class="ds-user-bubble">{html.escape(content)}</div>',
                    unsafe_allow_html=True,
                )
        return

    # Assistant message
    answer_col, _spacer = st.columns([0.86, 0.14])
    with answer_col:
        lang = msg.get("language")
        with st.container(border=True):
            if lang:
                st.caption(f"检测语言：{lang}")
            render_learning_signal(msg)
            st.markdown(content)


def render_chat_messages(messages: list[dict]) -> None:
    for msg in messages:
        render_message(msg)


def render_assistant_loading() -> None:
    answer_col, _spacer = st.columns([0.86, 0.14])
    with answer_col:
        with st.container(border=True):
            st.markdown(
                """
                <div class="ds-loading-bubble">
                    <span>正在分析代码并生成回答</span>
                    <span class="ds-loading-dots"><span></span><span></span><span></span></span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_chat_header(conversation: dict | None, n_messages: int) -> None:
    if not conversation:
        return
    title = conversation.get("title", "未命名代码对话")
    ts = conversation.get("updated_at") or conversation.get("created_at") or now_text()
    rounds = n_messages // 2
    meta = f"{rounds} 轮对话 | {ts}" if rounds else f"{n_messages} 条消息 | {ts}"
    st.markdown(f"### {title}")
    st.caption(meta)


# ── Agent Interaction ──────────────────────────────────────

def start_question(
    conversations: list[dict],
    current_id: str,
    question: str,
    *,
    image_bytes: bytes | None = None,
    image_mime: str = "",
    recognized_code: str = "",
    language: str | None = None,
) -> str:
    current_conv = get_conversation(conversations, current_id)
    if current_conv is None:
        current_id = create_conversation(conversations)
        st.session_state["code_current_id"] = current_id
        current_conv = get_conversation(conversations, current_id)

    if current_conv is None:
        return ""

    current_msgs = current_conv.setdefault("messages", [])
    msg_entry: dict = {"role": "user", "content": question}
    if image_bytes is not None:
        msg_entry["has_image"] = True
        msg_entry["image_size"] = len(image_bytes)
    if recognized_code:
        msg_entry["recognized_code"] = recognized_code
    if language:
        msg_entry["language"] = language
    current_msgs.append(msg_entry)

    current_conv["updated_at"] = now_text()
    ct = current_conv.get("title")
    if not ct or ct in {"新建代码对话", "未命名代码对话"}:
        current_conv["title"] = make_conversation_title(question)
    save_code_conversations(conversations)

    st.session_state["code_generating_id"] = current_id
    st.session_state["code_generating_question"] = question
    st.session_state["code_generating_image"] = image_bytes
    st.session_state["code_generating_image_mime"] = image_mime
    return current_id


def finish_pending_answer(conversations: list[dict]) -> None:
    current_id = str(st.session_state.get("code_generating_id") or "")
    question = str(st.session_state.get("code_generating_question") or "").strip()
    image_bytes = st.session_state.get("code_generating_image")
    image_mime = str(st.session_state.get("code_generating_image_mime") or "")

    if not current_id or not question:
        return

    current_conv = get_conversation(conversations, current_id)
    if current_conv is None:
        _cleanup_generating_state()
        return

    # Build chat history from recent messages for multi-turn context
    raw_msgs = current_conv.get("messages", []) or []
    # Exclude the last user message (already sent as current question)
    chat_history: list[dict[str, str]] = []
    for m in raw_msgs[-9:]:  # ~4 turns before current question
        role = m.get("role", "")
        content = str(m.get("content", ""))
        if role in ("user", "assistant") and content.strip():
            chat_history.append({"role": role, "content": content})

    try:
        agent = _get_agent()

        if image_bytes is not None and image_mime:
            with st.spinner("正在识别图片中的代码..."):
                result = agent.answer_with_image(question, image_bytes, image_mime, chat_history=chat_history)
        else:
            with st.spinner("正在分析代码..."):
                result = agent.answer_text_question(question, chat_history=chat_history)
    except RuntimeError as exc:
        error_msg = str(exc)
        from src.code_agent import CodeAgentAnswer
        result = CodeAgentAnswer(
            question=question,
            answer=f"出错了：{error_msg}\n\n请检查 `.env` 文件中的 API Key 配置。",
            has_image=image_bytes is not None,
            recognized_code=getattr(exc, "recognized_code", None),
        )
    except Exception as exc:
        from src.code_agent import CodeAgentAnswer
        result = CodeAgentAnswer(
            question=question,
            answer=f"回答生成失败：{exc}",
            has_image=False,
        )

    current_msgs = current_conv.setdefault("messages", [])
    assistant_msg: dict = {
        "role": "assistant",
        "content": result.answer,
    }
    if result.language:
        assistant_msg["language"] = result.language
    if result.recognized_code:
        assistant_msg["recognized_code"] = result.recognized_code
    if result.has_image:
        assistant_msg["has_image"] = True
    assistant_msg.update(result.learning_signal())
    current_msgs.append(assistant_msg)

    current_conv["learning_summary"] = {
        "topics": result.topics or [],
        "skills": result.skills or [],
        "difficulty": result.difficulty,
        "related_courses": result.related_courses or [],
        "next_exercises": result.next_exercises or [],
        "error_patterns": result.error_patterns or [],
    }
    current_conv["updated_at"] = now_text()
    save_code_conversations(conversations)
    update_profile_from_signal(
        question,
        {
            "topics": result.topics or [],
            "skills": result.skills or [],
            "difficulty": result.difficulty,
            "related_courses": result.related_courses or [],
            "next_exercises": result.next_exercises or [],
            "error_patterns": result.error_patterns or [],
        },
        answer=result.answer,
        language=result.language,
    )
    _cleanup_generating_state()


def _cleanup_generating_state() -> None:
    for key in (
        "code_generating_id",
        "code_generating_question",
        "code_generating_image",
        "code_generating_image_mime",
    ):
        st.session_state.pop(key, None)


# ── Main Page Renderer ──────────────────────────────────────

def render_code_learning_page() -> None:
    """Render the full Code Learning AI page."""
    apply_design_system()
    inject_extra_css(CODE_PAGE_CSS)
    render_top_nav("code")

    # Initialize session state
    st.session_state.setdefault("code_pending_question", None)
    st.session_state.setdefault("code_current_id", "")
    st.session_state.setdefault("code_show_upload", False)

    conversations = load_code_conversations()
    current_id = ensure_current_conversation(conversations)
    current_conv = get_conversation(conversations, current_id)
    current_msgs = current_conv.get("messages", []) if current_conv else []

    # Handle pending question from starter cards
    pending = st.session_state.get("code_pending_question")
    if pending:
        question = str(pending).strip()
        st.session_state["code_pending_question"] = None
        if question:
            start_question(conversations, current_id, question)
        st.rerun()

    # ── No messages yet -> show dashboard ──
    if not current_msgs:
        render_starter_dashboard(conversations)

        # Image upload area
        with st.expander("上传代码截图（可选）", expanded=st.session_state.get("code_show_upload", False)):
            if st.session_state.get("code_show_upload"):
                st.session_state["code_show_upload"] = False

            if not _get_agent().has_vision:
                st.info("图片识别功能需要配置 Kimi 视觉模型 API Key（在 `.env` 中设置 `CODE_VISION_API_KEY`）。文本代码问答仍可正常使用。")

            uploaded = st.file_uploader(
                "上传代码截图",
                type=["png", "jpg", "jpeg", "webp"],
                key="code_image_uploader",
                label_visibility="collapsed",
            )

            if uploaded is not None:
                img_bytes = uploaded.read()
                filename = uploaded.name or "screenshot.png"
                is_valid, error_msg = validate_image_upload(img_bytes, filename)
                if not is_valid:
                    st.error(error_msg)
                else:
                    st.image(img_bytes, caption="上传的代码截图", use_container_width=True)
                    st.session_state["code_uploaded_image"] = img_bytes

                    ext = Path(filename).suffix.lower()
                    st.session_state["code_uploaded_image_mime"] = EXT_TO_MIME.get(ext, "image/png")

        user_input = st.chat_input("输入代码问题，或粘贴代码片段...")
        if user_input and user_input.strip():
            question = user_input.strip()
            img_bytes = st.session_state.pop("code_uploaded_image", None)
            img_mime = st.session_state.pop("code_uploaded_image_mime", "")
            st.session_state["code_current_id"] = ""
            start_question(
                conversations, "",
                question,
                image_bytes=img_bytes,
                image_mime=img_mime,
            )
            st.rerun()
        return

    # ── Active conversation layout ──
    left, main = st.columns([0.24, 0.76], gap="large")

    with left:
        with st.container(border=True):
            render_sidebar(conversations, current_id)

    with main:
        hc, _mc = st.columns([8, 1])
        with hc:
            render_chat_header(current_conv, len(current_msgs))

        render_chat_messages(current_msgs)

        # Handle generating state
        generating_here = (
            str(st.session_state.get("code_generating_id") or "") == str(current_id)
            and bool(st.session_state.get("code_generating_question"))
        )
        if generating_here:
            render_assistant_loading()
            finish_pending_answer(conversations)
            st.rerun()

        render_quick_questions()

        # Image upload area (collapsed by default in active conversation)
        with st.expander("上传代码截图（可选）", expanded=False):
            if not _get_agent().has_vision:
                st.info("图片识别功能需要配置 Kimi 视觉模型 API Key（在 `.env` 中设置 `CODE_VISION_API_KEY`）。文本代码问答仍可正常使用。")

            uploaded = st.file_uploader(
                "上传代码截图",
                type=["png", "jpg", "jpeg", "webp"],
                key="code_image_uploader_active",
                label_visibility="collapsed",
            )

            if uploaded is not None:
                img_bytes = uploaded.read()
                filename = uploaded.name or "screenshot.png"
                is_valid, error_msg = validate_image_upload(img_bytes, filename)
                if not is_valid:
                    st.error(error_msg)
                else:
                    st.image(img_bytes, caption="上传的代码截图", use_container_width=True)
                    st.session_state["code_uploaded_image"] = img_bytes

                    ext = Path(filename).suffix.lower()
                    st.session_state["code_uploaded_image_mime"] = EXT_TO_MIME.get(ext, "image/png")

        # Chat input
        user_input = st.chat_input("输入代码问题，或粘贴代码片段...")
        if user_input and user_input.strip():
            question = user_input.strip()
            img_bytes = st.session_state.pop("code_uploaded_image", None)
            img_mime = st.session_state.pop("code_uploaded_image_mime", "")
            start_question(
                conversations, current_id,
                question,
                image_bytes=img_bytes,
                image_mime=img_mime,
            )
            st.rerun()
