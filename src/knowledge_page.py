from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from src.knowledge_summary import load_knowledge_summary
from src.ui.layout import apply_site_theme, ds_metric_card, render_top_nav, section_header


CATEGORY_NAMES: dict[str, str] = {
    "courses": "课程大纲",
    "programs": "培养方案",
    "web": "官网网页",
    "web_attachments": "官网附件",
}

CATEGORY_ORDERS: dict[str, int] = {
    "courses": 0,
    "programs": 1,
    "web": 2,
    "web_attachments": 3,
}


def load_build_report() -> dict:
    path = Path("data/processed/build_report.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def source_name(source_file: str) -> str:
    name = source_file.replace("\\", "/").split("/")[-1]
    for suffix in (".docx", ".doc", ".pdf", ".md", ".txt"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return name


def render_source_row(item: dict) -> None:
    title = str(item.get("title") or source_name(str(item.get("source_file") or "")) or "未命名资料")
    source_url = str(item.get("source_url") or "")
    site = str(item.get("site") or "")
    text_chars = item.get("text_chars", 0)
    chunks = item.get("chunks", 0)

    left, middle, right = st.columns([0.58, 0.24, 0.18])
    with left:
        st.markdown(f"**{html.escape(title)}**")
        source_file = source_name(str(item.get("source_file") or ""))
        if source_file and source_file != title:
            st.caption(source_file)
    with middle:
        st.caption(f"{text_chars:,} 字 · {chunks} 片段")
        if site:
            st.caption(site)
    with right:
        if source_url:
            st.link_button("打开来源", source_url, use_container_width=True)
        else:
            st.caption("本地文件")


def render_knowledge_base_page() -> None:
    apply_site_theme()
    render_top_nav("knowledge")

    summary = load_knowledge_summary()
    report = load_build_report()
    parsed = report.get("parsed", [])
    parsed = parsed if isinstance(parsed, list) else []

    st.markdown(
        f"""
        <section class="ds-hero">
            <div class="ds-hero-content">
                <div class="ds-hero-eyebrow">Knowledge Base · 数据资产</div>
                <h1>知识库资料</h1>
                <p>当前知识库已收录 <strong>{html.escape(str(summary["documents"]))}</strong> 份资料，
                拆分为 <strong>{html.escape(str(summary["chunks"]))}</strong> 个可检索片段。</p>
            </div>
            <div class="ds-hero-badges">
                <span class="ds-badge ds-badge-success">最近更新：{html.escape(str(summary["built_at"]))}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    section_header("数据总览")
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

    grouped: dict[str, list[dict]] = {}
    for item in parsed:
        grouped.setdefault(str(item.get("category") or "unknown"), []).append(item)

    section_header("资料分组")
    if not grouped:
        st.info("暂无资料入库记录，请先运行知识库构建脚本。")
        return

    for category, items in sorted(grouped.items(), key=lambda kv: CATEGORY_ORDERS.get(kv[0], 99)):
        label = f"{CATEGORY_NAMES.get(category, category)} · {len(items)} 项"
        with st.expander(label, expanded=(category == "courses")):
            for index, item in enumerate(items):
                render_source_row(item)
                if index != len(items) - 1:
                    st.divider()


def main() -> None:
    st.set_page_config(
        page_title="知识库资料",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_knowledge_base_page()


if __name__ == "__main__":
    main()
