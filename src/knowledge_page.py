from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from src.knowledge_summary import load_knowledge_summary
from src.ui.design_system import apply_design_system, inject_extra_css
from src.ui.layout import render_top_nav


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

CATEGORY_COLORS: dict[str, str] = {
    "courses": "#2E7D32",
    "programs": "#1565C0",
    "web": "#6A1B9A",
    "web_attachments": "#E65100",
}

KB_CSS = """
.ds-kb-kpi-row {
    display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 20px;
}
.ds-kb-kpi {
    border: 1px solid var(--border); border-radius: 12px;
    padding: 14px 16px; background: #fff;
    text-align: center; transition: box-shadow 150ms;
}
.ds-kb-kpi:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.06); }
.ds-kb-kpi-value { font-size: 1.4rem; font-weight: 750; color: var(--ink); }
.ds-kb-kpi-label { font-size: 0.74rem; color: var(--ink-muted); margin-top: 2px; }

.ds-kb-source-card {
    border: 1px solid var(--border); border-radius: 12px;
    padding: 16px 18px; background: #fff;
    transition: box-shadow 140ms; margin-bottom: 8px;
}
.ds-kb-source-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }

.ds-kb-cat-tag {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700; margin-right: 6px;
}
.ds-kb-source-link {
    display: inline-block; margin-top: 6px; padding: 4px 14px;
    border-radius: 6px; background: var(--ink); color: #fff !important;
    font-size: 0.78rem; font-weight: 650; text-decoration: none !important;
    transition: opacity 120ms;
}
.ds-kb-source-link:hover { opacity: 0.82; }

@media (max-width: 800px) {
    .ds-kb-kpi-row { grid-template-columns: repeat(2, 1fr); }
}
"""


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


def _file_icon(source_file: str) -> str:
    sf = source_file.lower()
    if sf.endswith(".pdf"):
        return "PDF"
    if sf.endswith((".docx", ".doc")):
        return "DOC"
    if sf.endswith(".md"):
        return "MD"
    if sf.endswith(".txt"):
        return "TXT"
    return "WEB"


def render_knowledge_base_page() -> None:
    apply_design_system()
    inject_extra_css(KB_CSS)
    render_top_nav("knowledge")

    summary = load_knowledge_summary()
    report = load_build_report()
    parsed = report.get("parsed", [])
    parsed = parsed if isinstance(parsed, list) else []

    # ── Hero ──
    st.markdown(
        f"""
        <section class="ds-hero">
            <div class="ds-hero-eyebrow">Knowledge Base</div>
            <h1>知识库资料</h1>
            <p>收录 <strong>{html.escape(str(summary["documents"]))}</strong> 份资料，
            拆分为 <strong>{html.escape(str(summary["chunks"]))}</strong> 个可检索片段，
            覆盖课程大纲、培养方案、官网页面与公开附件。</p>
            <div class="ds-hero-badges">
                <span class="ds-badge ds-badge-success">BGE 语义索引</span>
                <span class="ds-badge ds-badge-muted">最近更新：{html.escape(str(summary["built_at"]))}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # ── KPI row ──
    st.markdown("### 数据总览")
    st.html(
        f"""<div class="ds-kb-kpi-row">
            <div class="ds-kb-kpi">
                <div class="ds-kb-kpi-value">{summary['documents']}</div>
                <div class="ds-kb-kpi-label">资料文件</div>
            </div>
            <div class="ds-kb-kpi">
                <div class="ds-kb-kpi-value">{summary['chunks']}</div>
                <div class="ds-kb-kpi-label">知识片段</div>
            </div>
            <div class="ds-kb-kpi">
                <div class="ds-kb-kpi-value">{summary['courses']}</div>
                <div class="ds-kb-kpi-label">课程大纲</div>
            </div>
            <div class="ds-kb-kpi">
                <div class="ds-kb-kpi-value">{summary['web_pages']}</div>
                <div class="ds-kb-kpi-label">官网网页</div>
            </div>
            <div class="ds-kb-kpi">
                <div class="ds-kb-kpi-value">{summary['attachments']}</div>
                <div class="ds-kb-kpi-label">公开附件</div>
            </div>
        </div>"""
    )

    # ── Category summary cards ──
    grouped: dict[str, list[dict]] = {}
    total_chars = 0
    for item in parsed:
        grouped.setdefault(str(item.get("category") or "unknown"), []).append(item)
        total_chars += int(item.get("text_chars", 0))

    if not grouped:
        st.info("暂无资料入库记录，请先运行知识库构建脚本。")
        return

    # Category overview row
    cat_cols = st.columns(len(grouped))
    sorted_cats = sorted(grouped.items(), key=lambda kv: CATEGORY_ORDERS.get(kv[0], 99))
    for idx, (cat, items) in enumerate(sorted_cats):
        cat_chars = sum(int(i.get("text_chars", 0)) for i in items)
        cat_chunks = sum(int(i.get("chunks", 0)) for i in items)
        with cat_cols[idx]:
            with st.container(border=True):
                color = CATEGORY_COLORS.get(cat, "#666")
                st.markdown(
                    f'<span class="ds-kb-cat-tag" style="background:{color}18;color:{color}">'
                    f'{CATEGORY_NAMES.get(cat, cat)}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{len(items)} 项**")
                st.caption(f"{cat_chars:,} 字")
                st.caption(f"{cat_chunks} 片段")

    # ── Search ──
    st.markdown("---")
    st.markdown("### 资料明细")
    search = st.text_input("搜索资料", placeholder="输入文件名或标题关键词筛选...", label_visibility="collapsed")

    # ── Source list ──
    for category, items in sorted_cats:
        cat_name = CATEGORY_NAMES.get(category, category)
        filtered = items
        if search:
            q = search.lower()
            filtered = [
                i for i in items
                if q in str(i.get("title", "")).lower()
                or q in str(i.get("source_file", "")).lower()
                or q in str(i.get("site", "")).lower()
            ]
        if not filtered:
            continue

        color = CATEGORY_COLORS.get(category, "#666")
        with st.expander(f"{cat_name} ({len(filtered)} 项)", expanded=(category == "courses" and not search)):
            for item in filtered:
                title = str(item.get("title") or source_name(str(item.get("source_file") or "")) or "未命名资料")
                source_url = str(item.get("source_url") or "")
                site = str(item.get("site") or "")
                text_chars = item.get("text_chars", 0)
                chunks = item.get("chunks", 0)
                sf = source_name(str(item.get("source_file") or ""))
                ftype = _file_icon(str(item.get("source_file") or ""))

                link_html = ""
                if source_url:
                    link_html = (
                        f'<a class="ds-kb-source-link" href="{html.escape(source_url)}" '
                        f'target="_blank" rel="noopener">打开来源</a>'
                    )
                st.markdown(
                    f'<div class="ds-kb-source-card">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">'
                    f'<div style="flex:1;min-width:200px;">'
                    f'<strong style="color:var(--ink);">{html.escape(title)}</strong>'
                    f'<div style="font-size:0.78rem;color:var(--ink-muted);margin-top:4px;">'
                    f'<span class="ds-kb-cat-tag" style="background:{color}18;color:{color};">{ftype}</span>'
                    f'<span>{text_chars:,} 字</span>'
                    f'<span style="margin-left:8px;">{chunks} 片段</span>'
                    f'</div>'
                    f'</div>'
                    f'<div style="text-align:right;min-width:120px;">'
                    f'<div style="font-size:0.76rem;color:var(--ink-secondary);">{html.escape(site or sf)}</div>'
                    f'{link_html}'
                    f'</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def main() -> None:
    st.set_page_config(
        page_title="知识库资料",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_knowledge_base_page()


if __name__ == "__main__":
    main()
