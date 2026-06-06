from __future__ import annotations

import html

import streamlit as st

from src.ui.design_system import apply_design_system


def apply_site_theme() -> None:
    """Apply the global design system."""
    apply_design_system()


def render_top_nav(active: str) -> None:
    """Render the glassmorphism top navigation bar."""
    nav_items = [
        ("home", "🏠 主界面", "/?view=home"),
        ("chat", "💬 智能问答", "/?view=chat"),
        ("knowledge", "📚 知识库", "/?view=knowledge"),
    ]
    links = "".join(
        f'<a class="ds-topnav-link{" active" if key == active else ""}" '
        f'href="{href}" target="_self">{html.escape(label)}</a>'
        for key, label, href in nav_items
    )
    st.markdown(
        f"""
        <nav class="ds-topnav">
            <a class="ds-topnav-brand" href="/?view=home" target="_self">
                <span class="ds-topnav-logo">🎓</span>
                <span>高校教务教学智能体</span>
            </a>
            <div class="ds-topnav-links">{links}</div>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: object) -> None:
    """Render a premium metric card using legacy DS classes."""
    st.markdown(
        f"""
        <div class="metric-card">
            <span>{html.escape(str(label))}</span>
            <strong>{html.escape(str(value))}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── New design system metric card ─────────────────────────
METRIC_ICONS = {
    "资料文件": ("📄", "blue"),
    "知识片段": ("🧩", "coral"),
    "课程大纲": ("📋", "green"),
    "官网网页": ("🌐", "indigo"),
    "公开附件": ("📎", "amber"),
    "培养方案": ("📘", "blue"),
    "本地文件": ("📁", "blue"),
}


def ds_metric_card(label: str, value: object, *, accent: str = "blue") -> None:
    """Render a new design-system metric card with icon and hover effect."""
    icon_info = METRIC_ICONS.get(label, ("📊", accent))
    icon, icon_class = icon_info if isinstance(icon_info, tuple) else ("📊", accent)
    st.markdown(
        f"""
        <div class="ds-metric-card">
            <span class="ds-metric-icon {html.escape(icon_class)}">{icon}</span>
            <div>
                <div class="ds-metric-label">{html.escape(label)}</div>
                <div class="ds-metric-value">{html.escape(str(value))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str) -> None:
    """Render a section header with accent bar."""
    st.markdown(
        f'<div class="ds-section-title">{html.escape(title)}</div>',
        unsafe_allow_html=True,
    )


__all__ = [
    "apply_site_theme",
    "ds_metric_card",
    "metric_card",
    "render_top_nav",
    "section_header",
]
