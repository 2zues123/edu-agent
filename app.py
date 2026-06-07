from __future__ import annotations

import html

import streamlit as st

from src.chat_workspace import render_workspace_page
from src.conversations import load_conversations, visible_conversations
from src.knowledge_page import render_knowledge_base_page
from src.knowledge_summary import load_knowledge_summary
from src.ui.layout import apply_site_theme, ds_metric_card, render_top_nav, section_header


VALID_VIEWS = {"home", "chat", "knowledge"}


def first_query_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def current_view() -> str:
    view = str(first_query_value(st.query_params.get("view")) or "home")
    return view if view in VALID_VIEWS else "home"


def go_to(view: str) -> None:
    st.query_params["view"] = view
    st.rerun()


def render_home() -> None:
    apply_site_theme()
    render_top_nav("home")

    summary = load_knowledge_summary()
    conversations = load_conversations()
    recent = [item for item in visible_conversations(conversations) if item.get("messages")][:4]

    # ── Hero Section ────────────────────────────────
    st.markdown(
        """
        <section class="ds-hero">
            <div class="ds-hero-content">
                <div class="ds-hero-eyebrow">AI-Powered · 知识即服务</div>
                <h1>高校教务教学智能体</h1>
                <p>基于 RAG 架构的教务知识引擎，将课程大纲、培养方案、官网公告和历史问答智能拆解为结构化知识模块。
                一站式查询、精准溯源、秒级响应。</p>
            </div>
            <div class="ds-hero-badges">
                <span class="ds-badge ds-badge-success">● 知识库在线</span>
                <span class="ds-badge ds-badge-muted">本地运行</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # ── Core Action Cards ───────────────────────────
    card_col1, card_col2 = st.columns(2)
    with card_col1:
        st.markdown(
            """
            <div class="ds-card ds-card-primary">
                <div class="ds-card-kicker">核心模块</div>
                <div class="ds-card-title">💬 智能问答工作台</div>
                <div class="ds-card-desc">基于教务知识库的智能检索与对话。支持课程查询、大纲解读、学分核对、
                培养方案问答，每次回答均附带可溯源的资料依据。</div>
                <a class="ds-btn-primary" href="/?view=chat" target="_self">
                    进入工作台 →
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with card_col2:
        st.markdown(
            """
            <div class="ds-card">
                <div class="ds-card-kicker">资料模块</div>
                <div class="ds-card-title">📚 知识库资料</div>
                <div class="ds-card-desc">查看当前 RAG 知识库已入库的所有资料，包含本地课程文档、培养方案、
                官网网页与公开附件，实时追踪知识库更新状态。</div>
                <a class="ds-btn-outline" href="/?view=knowledge" target="_self">
                    查看知识库 →
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Metrics Grid ────────────────────────────────
    section_header("知识库概览")
    metric_cols = st.columns(5)
    metric_data = [
        ("资料文件", summary["documents"], "blue"),
        ("知识片段", summary["chunks"], "coral"),
        ("课程大纲", summary["courses"], "green"),
        ("官网网页", summary["web_pages"], "indigo"),
        ("公开附件", summary["attachments"], "amber"),
    ]
    for column, (label, value, accent) in zip(metric_cols, metric_data):
        with column:
            ds_metric_card(label, value, accent=accent)

    st.markdown(
        f'<div class="ds-timestamp">🕐 最近更新：{html.escape(str(summary["built_at"]))}</div>',
        unsafe_allow_html=True,
    )

    # ── Recent Activity ─────────────────────────────
    if recent:
        section_header("最近对话")
        st.markdown('<div class="ds-recent-list">', unsafe_allow_html=True)
        for conversation in recent:
            title = html.escape(conversation.get("title") or "未命名教务对话")
            updated_at = html.escape(
                conversation.get("updated_at") or conversation.get("created_at") or ""
            )
            count = len(conversation.get("messages", []))
            st.markdown(
                f"""
                <div class="ds-recent-item">
                    <div class="ds-recent-left">
                        <span class="ds-recent-dot"></span>
                        <span class="ds-recent-title">{title}</span>
                    </div>
                    <span class="ds-recent-meta">{count} 条消息 · {updated_at}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="高校教务教学智能体",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    view = current_view()
    if view == "chat":
        render_workspace_page(configure_page=False)
        return
    if view == "knowledge":
        render_knowledge_base_page()
        return
    render_home()


if __name__ == "__main__":
    main()
