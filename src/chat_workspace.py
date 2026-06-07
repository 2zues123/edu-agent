from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import streamlit as st

from src.graph import GraphAgentAnswer, LangGraphAcademicAgent
from src.retriever import RetrievedChunk
from src.ui.design_system import apply_design_system
from src.ui.layout import render_top_nav

EXAMPLE_QUESTIONS = (
    "机器学习课程多少学分？",
    "数字图像处理课程的考核方式是什么？",
    "2024培养方案的软件工程专业毕业要求是什么？",
    "如果挂科会影响毕业吗？",
    "人工智能导论有哪些先修课程？",
)

LEGACY_HISTORY_FILE = Path(".chat_history/history.json")
CONVERSATIONS_FILE = Path(".chat_history/conversations.json")
MAX_HISTORY_ITEMS = 20
QUICK_QUESTION_COUNT = 4

KNOWLEDGE_CACHE_FILES = [
    "data/processed/chunks.jsonl",
    "data/index/faiss/metadata.jsonl",
    "data/index/faiss/index_config.json",
]

STARTER_CARDS = (
    ("课程信息", "green", "●", "学分、学时、先修课", "机器学习课程多少学分？"),
    ("课程大纲", "blue", "●", "平时、实验、期末占比", "数字图像处理课程的考核方式是什么？"),
    ("培养方案", "amber", "●", "毕业要求与课程模块", "2024培养方案的软件工程专业毕业要求是什么？"),
    ("学业风险", "rose", "●", "挂科、重修、毕业影响", "如果挂科会影响毕业吗？"),
)


def knowledge_cache_stamp() -> tuple[tuple[str, int, int], ...]:
    stamp: list[tuple[str, int, int]] = []
    for path in KNOWLEDGE_CACHE_FILES:
        try:
            stat = Path(path).stat()
            stamp.append((str(path), int(stat.st_mtime_ns), int(stat.st_size)))
        except OSError:
            pass
    return tuple(stamp)


@st.cache_resource(show_spinner=False)
def load_agent(_cache_stamp: tuple[tuple[str, int, int], ...]) -> LangGraphAcademicAgent:
    return LangGraphAcademicAgent()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def make_conversation_title(question: str) -> str:
    return question.strip().replace("\n", " ").replace("\r", "")


def normalize_conversation(conversation: dict) -> dict:
    conversation.setdefault("id", str(uuid4()))
    conversation.setdefault("messages", [])
    conversation.setdefault("created_at", now_text())
    conversation.setdefault("updated_at", conversation.get("created_at", now_text()))
    conversation.setdefault("title", "未命名教务对话")
    conversation.setdefault("pinned", False)
    return conversation


def conversation_has_messages(conversation: dict) -> bool:
    return bool(conversation.get("messages"))


def compact_empty_conversations(conversations: list[dict], keep_id: str | None = None) -> None:
    """Remove duplicate empty conversations while optionally keeping the active draft."""
    kept_empty = False
    compacted: list[dict] = []
    for conversation in conversations:
        if conversation_has_messages(conversation):
            compacted.append(conversation)
            continue
        cid = str(conversation.get("id", ""))
        if keep_id and cid == keep_id:
            compacted.append(conversation)
            kept_empty = True
        elif not kept_empty and not keep_id:
            compacted.append(conversation)
            kept_empty = True
    conversations.clear()
    conversations.extend(compacted)


def load_legacy_history() -> list[dict]:
    if not LEGACY_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(LEGACY_HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    migrated: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or item.get("user", "")).strip()
        answer = str(item.get("answer") or item.get("assistant", "")).strip()
        if not question and not answer:
            continue
        created_at = str(item.get("timestamp") or item.get("created_at") or now_text())
        conversation = {
            "id": str(item.get("id") or uuid4()),
            "title": make_conversation_title(question),
            "created_at": created_at,
            "updated_at": created_at,
            "messages": [],
            "pinned": False,
        }
        if question:
            conversation["messages"].append({"role": "user", "content": question})
        if answer:
            conversation["messages"].append({"role": "assistant", "content": answer, "result": None})
        migrated.append(conversation)
    return migrated


def load_conversations() -> list[dict]:
    if not CONVERSATIONS_FILE.exists():
        migrated = load_legacy_history()
        if migrated:
            save_conversations(migrated)
        return migrated
    try:
        data = json.loads(CONVERSATIONS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = load_legacy_history()
        if data:
            save_conversations(data)
        return data
    if not isinstance(data, list):
        data = []
    conversations = [normalize_conversation(item) for item in data if isinstance(item, dict)]
    original_count = len(conversations)
    compact_empty_conversations(conversations)
    if len(conversations) != original_count:
        save_conversations(conversations)
    return conversations


def save_conversations(conversations: list[dict], keep_empty_id: str | None = None) -> None:
    CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    normalized = list(conversations)
    compact_empty_conversations(normalized, keep_empty_id)
    if len(normalized) > MAX_HISTORY_ITEMS:
        normalized = normalized[-MAX_HISTORY_ITEMS:]
    CONVERSATIONS_FILE.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_history() -> None:
    if CONVERSATIONS_FILE.exists():
        CONVERSATIONS_FILE.unlink()
    if LEGACY_HISTORY_FILE.exists():
        LEGACY_HISTORY_FILE.unlink()


def create_conversation(conversations: list[dict]) -> str:
    compact_empty_conversations(conversations)
    timestamp = now_text()
    cid = str(uuid4())
    conversations.insert(0, {
        "id": cid, "title": "新建教务对话",
        "created_at": timestamp, "updated_at": timestamp,
        "messages": [], "pinned": False,
    })
    save_conversations(conversations, keep_empty_id=cid)
    return cid


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


def ensure_current_conversation(conversations: list[dict]) -> str:
    cid = st.session_state.get("current_conversation_id", "")
    c = get_conversation(conversations, cid if cid else None)
    if c is None:
        cid = create_conversation(conversations)
        st.session_state["current_conversation_id"] = cid
    return cid


def sorted_conversations(conversations: list[dict]) -> list[dict]:
    return sorted(conversations, key=lambda i: (bool(i.get("pinned")), conversation_timestamp(i)), reverse=True)


def visible_conversations(conversations: list[dict]) -> list[dict]:
    return [item for item in sorted_conversations(conversations) if conversation_has_messages(item)]


def toggle_conversation_pin(conversations: list[dict], cid: str) -> None:
    c = get_conversation(conversations, cid)
    if c is not None:
        c["pinned"] = not bool(c.get("pinned"))
        c["updated_at"] = now_text()
        save_conversations(conversations)


def rename_conversation(conversations: list[dict], cid: str, title: str) -> None:
    c = get_conversation(conversations, cid)
    if c is not None:
        t = title.strip()
        if t:
            c["title"] = t
            c["updated_at"] = now_text()
            save_conversations(conversations)


def delete_conversation(conversations: list[dict], cid: str) -> str:
    remaining = [i for i in conversations if i.get("id") != cid]
    conversations.clear()
    conversations.extend(remaining)
    if not conversations:
        new_id = create_conversation(conversations)
    else:
        v = visible_conversations(conversations)
        new_id = v[0].get("id", "") if v else create_conversation(conversations)
    save_conversations(conversations)
    return new_id


def source_attr(source: RetrievedChunk, name: str, default: str = "") -> str:
    value = getattr(source, name, default)
    return default if value is None else str(value)


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def source_to_dict(source: RetrievedChunk) -> dict:
    return {
        "chunk_id": source_attr(source, "chunk_id"),
        "title": source_attr(source, "title"),
        "category": source_attr(source, "category"),
        "source_file": source_attr(source, "source_file"),
        "heading": source_attr(source, "heading"),
        "text": source_attr(source, "text"),
        "score": safe_float(getattr(source, "score", 0.0)),
        "source_url": source_attr(source, "source_url"),
        "site": source_attr(source, "site"),
        "published_at": source_attr(source, "published_at"),
    }


def source_from_dict(data: dict) -> RetrievedChunk:
    base = {
        "chunk_id": str(data.get("chunk_id", "")),
        "title": str(data.get("title", "")),
        "category": str(data.get("category", "")),
        "source_file": str(data.get("source_file", "")),
        "heading": str(data.get("heading", "")),
        "text": str(data.get("text", "")),
        "score": safe_float(data.get("score"), 0.0),
    }
    extra = {
        "source_url": str(data.get("source_url", "")),
        "site": str(data.get("site", "")),
        "published_at": str(data.get("published_at", "")),
    }
    try:
        return RetrievedChunk(**base, **extra)
    except TypeError:
        return SimpleNamespace(**base, **extra)


def result_to_dict(result: GraphAgentAnswer) -> dict:
    return {
        "question": result.question,
        "intent_name": result.intent_name,
        "intent_description": result.intent_description,
        "high_risk": result.high_risk,
        "answer": result.answer,
        "sources": [source_to_dict(s) for s in result.sources],
    }


def result_from_dict(data: dict) -> GraphAgentAnswer:
    raw = data.get("sources", [])
    if not isinstance(raw, list):
        raw = []
    return GraphAgentAnswer(
        question=str(data.get("question", "")),
        intent_name=str(data.get("intent_name", "general")),
        intent_description=str(data.get("intent_description", "")),
        high_risk=bool(data.get("high_risk", False)),
        answer=str(data.get("answer", "")),
        sources=[source_from_dict(s) for s in raw],
    )


def highlight_source_text(text: str, heading: str) -> str:
    escaped = html.escape(text)
    keywords = [heading.strip()] if heading.strip() else []
    for line in text.splitlines():
        m = re.match(r"^[一二三四五六七八九十]+[、.．]", line.strip())
        if m:
            keywords.append(m.group(0))
    for kw in list(dict.fromkeys(keywords)):
        if kw:
            escaped = escaped.replace(html.escape(kw), f"<mark>{html.escape(kw)}</mark>")
    return escaped


def load_knowledge_summary() -> dict:
    rf = Path("data/processed/build_report.json")
    cf = Path("data/processed/chunks.jsonl")
    summary = {"documents": 0, "chunks": 0, "built_at": "本地知识库"}
    if rf.exists():
        try:
            r = json.loads(rf.read_text(encoding="utf-8"))
            parsed = r.get("parsed", [])
            summary["documents"] = int(r.get("parsed_count") or r.get("document_count") or 0)
            summary["chunks"] = int(r.get("chunk_count") or 0)
            bt = str(r.get("built_at") or "")
            if bt:
                summary["built_at"] = bt[:10]
        except (OSError, ValueError, TypeError):
            pass
    if not summary["chunks"] and cf.exists():
        try:
            summary["chunks"] = sum(1 for l in cf.read_text(encoding="utf-8").splitlines() if l.strip())
        except OSError:
            pass
    return summary


# ── UI Rendering ─────────────────────────────────────────


def render_empty_dashboard(conversations: list[dict]) -> None:
    st.markdown(
        """
        <section class="ds-hero">
            <div class="ds-hero-eyebrow">HebTU Agent · 智能教务服务</div>
            <h1>高校对话系统</h1>
            <p>基于教务知识库的智能检索与对话，支持课程查询、培养方案问答、
            办事流程引导，每次回答均附带可溯源的资料依据。</p>
            <div class="ds-hero-badges">
                <span class="ds-badge ds-badge-success">课程咨询</span>
                <span class="ds-badge ds-badge-muted">培养方案</span>
                <span class="ds-badge ds-badge-muted">资料溯源</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.caption("选择一个场景快速开始，或直接在下方输入你的问题")

    card_cols = st.columns(4)
    for idx, (col, card) in enumerate(zip(card_cols, STARTER_CARDS)):
        label, accent, icon, desc, question = card
        with col:
            with st.container(border=True):
                st.markdown(f"**{icon}  {label}**")
                st.caption(desc)
                if st.button("开始提问 →", key=f"starter_{idx}", use_container_width=True):
                    st.session_state["pending_question"] = question
                    st.rerun()


def render_quick_questions() -> None:
    st.caption("💡 试试这些问题")
    cols = st.columns(QUICK_QUESTION_COUNT)
    for i, q in enumerate(EXAMPLE_QUESTIONS[:QUICK_QUESTION_COUNT]):
        with cols[i]:
            if st.button(q, key=f"qq_{i}", use_container_width=True):
                st.session_state["pending_question"] = q
                st.rerun()


def render_chat_header(conversation: dict | None, n_messages: int) -> None:
    if not conversation:
        return
    title = conversation.get("title", "未命名教务对话")
    ts = conversation.get("updated_at") or conversation.get("created_at") or now_text()
    rounds = n_messages // 2
    meta = f"{rounds} 轮对话 · {ts}" if rounds else f"{n_messages} 条消息 · {ts}"
    st.markdown(f"### {title}")
    st.caption(meta)


def render_message(msg: dict) -> None:
    role = msg.get("role", "user")
    with st.chat_message(role):
        if role == "assistant" and msg.get("result"):
            render_answer(result_from_dict(msg["result"]))
        else:
            st.markdown(str(msg.get("content", "")))


def render_conversation_actions(conversations: list[dict], conversation: dict) -> None:
    cid = str(conversation.get("id", ""))
    with st.popover("⋯", use_container_width=True):
        pin_label = "📌 取消置顶" if conversation.get("pinned") else "📌 置顶对话"
        if st.button(pin_label, key=f"pin_{cid}", use_container_width=True):
            toggle_conversation_pin(conversations, cid)
            st.rerun()
        if st.button("✏️ 重命名", key=f"rn_btn_{cid}", use_container_width=True):
            st.session_state["renaming_id"] = cid
        if st.session_state.get("renaming_id") == cid:
            nt = st.text_input("新标题", value=str(conversation.get("title", "")), key=f"rn_inp_{cid}", label_visibility="collapsed")
            sc, cc = st.columns(2)
            with sc:
                if st.button("保存", key=f"rn_sv_{cid}", use_container_width=True):
                    rename_conversation(conversations, cid, nt)
                    st.session_state.pop("renaming_id", None)
                    st.rerun()
            with cc:
                if st.button("取消", key=f"rn_ccl_{cid}", use_container_width=True):
                    st.session_state.pop("renaming_id", None)
                    st.rerun()
        if st.button("🗑️ 删除对话", key=f"del_btn_{cid}", use_container_width=True):
            st.session_state["delete_id"] = cid
        if st.session_state.get("delete_id") == cid:
            st.warning("确定删除此对话？")
            dc, ca = st.columns(2)
            with dc:
                if st.button("确定", key=f"del_cfm_{cid}", use_container_width=True):
                    nid = delete_conversation(conversations, cid)
                    st.session_state["current_conversation_id"] = nid
                    st.session_state.pop("delete_id", None)
                    st.rerun()
            with ca:
                if st.button("取消", key=f"del_ccl_{cid}", use_container_width=True):
                    st.session_state.pop("delete_id", None)
                    st.rerun()


def render_answer(result: GraphAgentAnswer) -> None:
    if result.high_risk:
        st.warning("该问题涉及正式教务认定，系统仅根据当前知识库做初步判断，最终结果以教务系统、学院和教务部门审核为准。")

    chips = [f"意图：{result.intent_name}{'（' + result.intent_description + '）' if result.intent_description else ''}"]
    if result.high_risk:
        chips.append("⚠️ 高风险")
    if result.sources:
        chips.append(f"📎 引用 {len(result.sources)} 项依据")
    st.caption(" · ".join(chips))

    st.markdown(result.answer)

    if result.sources:
        with st.expander(f"📚 查看 {len(result.sources)} 项资料依据"):
            for i, source in enumerate(result.sources):
                heading = source_attr(source, "heading") or "未识别章节"
                title = source_attr(source, "title") or "未命名资料"
                category = source_attr(source, "category") or "未知分类"
                source_file = source_attr(source, "source_file") or "未知来源"
                text = source_attr(source, "text")
                source_url = source_attr(source, "source_url")
                site = source_attr(source, "site")
                published_at = source_attr(source, "published_at")

                st.markdown(f"**[资料{i + 1}] {html.escape(title)}**")
                st.caption(f"📂 {html.escape(category)} · 📄 {html.escape(source_file)} · 📍 {html.escape(heading)}")
                if site:
                    st.caption(f"🌐 {html.escape(site)}")
                if published_at:
                    st.caption(f"🕐 {html.escape(published_at)}")
                if source_url:
                    st.link_button("打开来源", source_url)

                hl = highlight_source_text(text, heading)
                st.markdown(
                    f'<div class="ds-source-text">{hl}</div>',
                    unsafe_allow_html=True,
                )
                st.divider()


def render_workspace_sidebar(conversations: list[dict], current_id: str) -> None:
    summary = load_knowledge_summary()
    st.markdown("#### 河北师大教务智能体")

    if st.button("＋ 新建对话", key="new_conv", use_container_width=True):
        nid = create_conversation(conversations)
        st.session_state["current_conversation_id"] = nid
        st.rerun()

    st.caption(f"知识库：{summary['documents']} 份资料 · {summary['chunks']} 片段")

    st.markdown("---")

    recent = visible_conversations(conversations)[:MAX_HISTORY_ITEMS]
    if recent:
        st.caption("📋 历史对话")

    for i, c in enumerate(recent):
        cid = str(c.get("id", ""))
        ct = str(c.get("title") or "未命名教务对话")
        pinned = c.get("pinned")
        display = f"📌 {ct}" if pinned else ct

        tc, mc = st.columns([0.84, 0.16])
        with tc:
            bt = "primary" if cid == current_id else "secondary"
            if st.button(display, key=f"hist_{i}", use_container_width=True, type=bt):
                st.session_state["current_conversation_id"] = cid
                st.rerun()
        with mc:
            render_conversation_actions(conversations, c)

    if recent:
        if st.button("🗑️ 清空历史", key="clr_hist", use_container_width=True):
            clear_history()
            st.session_state["current_conversation_id"] = str(uuid4())
            st.rerun()


def render_workspace_page(configure_page: bool = False) -> None:
    if configure_page:
        st.set_page_config(
            page_title="智能问答工作台", page_icon="💬",
            layout="wide", initial_sidebar_state="collapsed",
        )

    apply_design_system()
    render_top_nav("chat")

    st.session_state.setdefault("pending_question", None)
    st.session_state.setdefault("current_conversation_id", "")
    st.session_state.setdefault("cfg_use_llm", True)
    st.session_state.setdefault("cfg_top_k", 5)

    conversations = load_conversations()
    current_id = ensure_current_conversation(conversations)
    current_conv = get_conversation(conversations, current_id)
    current_msgs = current_conv.get("messages", []) if current_conv else []

    left, main = st.columns([0.25, 0.75], gap="large")

    with left:
        with st.container(border=True):
            render_workspace_sidebar(conversations, current_id)

    with main:
        hc, mc = st.columns([8, 1])
        with hc:
            render_chat_header(current_conv, len(current_msgs))
        with mc:
            with st.popover("⚙️", use_container_width=True):
                use_llm = st.toggle("调用大模型", value=st.session_state["cfg_use_llm"], key="cfg_use_llm_toggle")
                st.session_state["cfg_use_llm"] = use_llm
                top_k = st.slider("检索片段数", 1, 20, st.session_state["cfg_top_k"], key="cfg_top_k_slider")
                st.session_state["cfg_top_k"] = top_k

        if not current_msgs:
            render_empty_dashboard(conversations)
        else:
            for msg in current_msgs:
                render_message(msg)
            st.divider()

        render_quick_questions()

        user_input = st.chat_input("输入你的教务问题...")
        pending = st.session_state.get("pending_question")
        question = ""
        if user_input:
            question = user_input.strip()
            st.session_state["pending_question"] = None
        elif pending:
            question = str(pending).strip()
            st.session_state["pending_question"] = None

        if not question:
            return

        current_msgs.append({"role": "user", "content": question})
        if not current_conv:
            current_id = create_conversation(conversations)
            current_conv = get_conversation(conversations, current_id)

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("正在检索知识库并生成回答..."):
                try:
                    agent = load_agent(knowledge_cache_stamp())
                    result = agent.answer(question, top_k=st.session_state["cfg_top_k"], use_llm=st.session_state["cfg_use_llm"])
                except Exception as exc:
                    result = GraphAgentAnswer(
                        question=question, intent_name="general",
                        intent_description="通用问题", high_risk=False,
                        answer=f"抱歉，回答生成失败：{exc}", sources=[],
                    )
            render_answer(result)

        current_msgs.append({"role": "assistant", "content": result.answer, "result": result_to_dict(result)})

        if current_conv is not None:
            current_conv["messages"] = current_msgs
            current_conv["updated_at"] = now_text()
            ct = current_conv.get("title")
            if not ct or ct == "新建教务对话":
                current_conv["title"] = make_conversation_title(question)
            save_conversations(conversations)

        st.rerun()


def main() -> None:
    render_workspace_page(configure_page=True)


if __name__ == "__main__":
    main()
