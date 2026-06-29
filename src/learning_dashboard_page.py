"""Learning cockpit page for the Software College growth agent."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import streamlit as st

from src.learner_profile import load_profile, recommended_tasks, update_basic_profile
from src.learning_map import build_learning_map, load_learning_map, save_learning_map
from src.ui.design_system import apply_design_system, inject_extra_css
from src.ui.layout import render_top_nav


CODE_CONVERSATIONS_FILE = Path(".chat_history/code_conversations.json")

# Heuristic: detect text that looks like code rather than natural language
_CODE_INDICATORS = [
    re.compile(r"\b(def|class|import|return|print|while|for|if|else|elif)\b"),
    re.compile(r"[{}();]"),
    re.compile(r"^\s*(#|//|/\*)"),
    re.compile(r"\b(public|private|static|void|int|float|double|String)\b"),
    re.compile(r"\b(len|range|append|split|join|lambda|yield|raise|except|try|catch)\b"),
]


LEARNING_DASHBOARD_CSS = """
.learn-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
    gap: 18px;
    align-items: stretch;
    margin: 10px 0 18px;
}
.learn-panel {
    border: 1px solid var(--border);
    border-radius: 18px;
    background: rgba(255, 249, 239, 0.84);
    box-shadow: var(--shadow-sm);
    padding: 20px;
}
.learn-panel h1,
.learn-panel h2,
.learn-panel h3 {
    margin: 0 0 10px;
    color: var(--ink);
}
.learn-panel p {
    margin: 0;
    color: var(--ink-secondary);
    line-height: 1.7;
}
.learn-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 12px 0 18px;
}
.learn-kpi {
    border: 1px solid rgba(24, 53, 35, 0.12);
    border-radius: 12px;
    padding: 14px;
    background: rgba(255,255,255,0.54);
}
.learn-kpi span {
    display: block;
    color: var(--ink-muted);
    font-size: 0.78rem;
    font-weight: 700;
}
.learn-kpi strong {
    display: block;
    margin-top: 6px;
    color: var(--ink);
    font-size: 1.3rem;
}
.learn-skill {
    display: grid;
    grid-template-columns: 92px minmax(0, 1fr) 42px;
    gap: 12px;
    align-items: center;
    margin: 11px 0;
}
.learn-skill-name,
.learn-skill-score {
    color: var(--ink-secondary);
    font-size: 0.84rem;
    font-weight: 700;
}
.learn-skill-track {
    height: 10px;
    border-radius: 999px;
    background: rgba(23, 50, 74, 0.08);
    overflow: hidden;
}
.learn-skill-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #168C8C, #7FB8A4);
}
.learn-tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}
.learn-tag {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 0 10px;
    border-radius: 999px;
    background: #DDEAE2;
    color: #168C8C;
    font-size: 0.78rem;
    font-weight: 750;
}
.learn-task {
    border-left: 3px solid #168C8C;
    padding: 10px 0 10px 14px;
    margin: 8px 0;
}
.learn-task strong {
    display: block;
    color: var(--ink);
}
.learn-task span {
    color: var(--ink-secondary);
    font-size: 0.86rem;
}
.learn-course-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}
.learn-course {
    border: 1px solid rgba(24, 53, 35, 0.10);
    border-radius: 12px;
    padding: 12px;
    background: rgba(255,255,255,0.48);
}
.learn-course strong {
    display: block;
    color: var(--ink);
}
.learn-course span {
    color: var(--ink-muted);
    font-size: 0.78rem;
}
@media (max-width: 860px) {
    .learn-hero,
    .learn-kpi-grid,
    .learn-course-grid {
        grid-template-columns: 1fr;
    }
}
"""


def _looks_like_code(text: str) -> bool:
    """Heuristic to detect whether text looks like source code rather than natural language."""
    if not text or not text.strip():
        return False
    return sum(1 for pattern in _CODE_INDICATORS if pattern.search(text)) >= 2


def _task_label(task: dict[str, Any]) -> str:
    """Build a human-readable label for a task, avoiding raw-question exposure."""
    topics = task.get("topics", [])
    difficulty = str(task.get("difficulty", ""))
    if topics:
        readable = [str(t) for t in topics[:3] if str(t).strip()]
        if readable:
            return " · ".join(readable[:2])
    if difficulty and difficulty != "入门":
        return f"{difficulty}难度练习"
    return "代码学习记录"


def _task_detail(task: dict[str, Any]) -> str:
    """Build a detail line for a task from metadata (skills + courses)."""
    parts: list[str] = []
    skills = task.get("skills", [])
    if skills:
        parts.append("技能：" + "、".join(str(s) for s in skills[:2] if str(s).strip()))
    courses = task.get("related_courses", [])
    if courses:
        parts.append("课程：" + "、".join(str(c) for c in courses[:2] if str(c).strip()))
    return " · ".join(parts) if parts else ""


def render_learning_dashboard_page() -> None:
    apply_design_system()
    inject_extra_css(LEARNING_DASHBOARD_CSS)
    render_top_nav("learn")

    profile = load_profile()
    learning_map = load_learning_map()
    code_conversations = load_code_conversations()

    render_header(profile, learning_map, code_conversations)
    render_profile_editor(profile)

    left, right = st.columns([0.62, 0.38], gap="large")
    with left:
        render_skill_scores(profile)
        render_recommended_tasks(profile)
        render_learning_map_summary(learning_map)
    with right:
        render_weak_topics(profile)
        render_recent_activity(profile, code_conversations)
        render_map_actions()


def render_header(profile: dict[str, Any], learning_map: dict[str, Any], code_conversations: list[dict[str, Any]]) -> None:
    basic = profile.get("basic", {})
    weak_topics = profile.get("knowledge_state", {}).get("weak_topics", [])
    recent_tasks = profile.get("activity", {}).get("recent_tasks", [])
    kpis = [
        ("目标", basic.get("goal", "课程补弱")),
        ("薄弱点", len(weak_topics)),
        ("代码对话", len(code_conversations)),
        ("课程节点", len(learning_map.get("courses", []))),
    ]
    kpi_markup = "".join(
        f'<div class="learn-kpi"><span>{html.escape(str(label))}</span><strong>{html.escape(str(value))}</strong></div>'
        for label, value in kpis
    )
    # Build a safe summary label for the most recent task (never expose raw question)
    if recent_tasks and isinstance(recent_tasks[0], dict):
        recent_label = _task_label(recent_tasks[0])
    else:
        recent_label = "暂无"
    st.html(
        f"""<section class="learn-hero">
            <div class="learn-panel">
                <h1>学习驾驶舱</h1>
                <p>把教务资料、课程地图、代码学习记录和个人薄弱点合在一起，形成软件学院专属的成长型学习 Agent。</p>
                <div class="learn-kpi-grid">{kpi_markup}</div>
            </div>
            <div class="learn-panel">
                <h3>当前画像</h3>
                <p>年级：{html.escape(str(basic.get("grade", "未设置")))}</p>
                <p>方向：{html.escape(str(basic.get("direction", "软件工程综合能力")))}</p>
                <p>最近学习：{html.escape(recent_label)}</p>
            </div>
        </section>"""
    )


def render_profile_editor(profile: dict[str, Any]) -> None:
    basic = profile.get("basic", {})
    with st.expander("调整学习目标", expanded=False):
        with st.form("learner_profile_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                grade = st.text_input("年级", value=str(basic.get("grade", "未设置")))
            with c2:
                goal = st.text_input("目标", value=str(basic.get("goal", "课程补弱与代码能力提升")))
            with c3:
                direction = st.text_input("方向", value=str(basic.get("direction", "软件工程综合能力")))
            submitted = st.form_submit_button("保存画像", use_container_width=True)
            if submitted:
                update_basic_profile(grade=grade, goal=goal, direction=direction)
                st.success("学习画像已更新")
                st.rerun()


def render_skill_scores(profile: dict[str, Any]) -> None:
    scores = profile.get("coding_state", {}).get("skill_scores", {})
    rows = []
    for name, value in scores.items():
        try:
            score = max(0, min(100, int(value)))
        except (TypeError, ValueError):
            score = 0
        rows.append(
            f"""<div class="learn-skill">
                <div class="learn-skill-name">{html.escape(str(name))}</div>
                <div class="learn-skill-track"><div class="learn-skill-fill" style="width:{score}%"></div></div>
                <div class="learn-skill-score">{score}</div>
            </div>"""
        )
    st.html(
        f'<div class="learn-panel"><h2>能力雷达</h2>{"".join(rows)}</div>'
    )


def render_recommended_tasks(profile: dict[str, Any]) -> None:
    task_markup = []
    for task in recommended_tasks(profile):
        task_markup.append(
            f"""<div class="learn-task">
                <strong>{html.escape(str(task.get("title", "")))}</strong>
                <span>{html.escape(str(task.get("detail", "")))}</span>
            </div>"""
        )
    st.html(
        f'<div class="learn-panel"><h2>本周推荐任务</h2>{"".join(task_markup)}</div>'
    )


def render_learning_map_summary(learning_map: dict[str, Any]) -> None:
    courses = learning_map.get("courses", [])[:8]
    course_markup = []
    for course in courses:
        course_markup.append(
            f"""<div class="learn-course">
                <strong>{html.escape(str(course.get("name", "")))}</strong>
                <span>{html.escape(str(course.get("type", "专业课程")))} · 权重 {html.escape(str(course.get("weight", 0)))}</span>
            </div>"""
        )
    st.html(
        f'<div class="learn-panel"><h2>课程能力地图</h2><div class="learn-course-grid">{"".join(course_markup)}</div></div>'
    )


def render_weak_topics(profile: dict[str, Any]) -> None:
    state = profile.get("knowledge_state", {})
    topics = _tag_markup(state.get("weak_topics", []))
    courses = _tag_markup(state.get("related_courses", []))
    errors = _tag_markup(profile.get("coding_state", {}).get("error_patterns", []))
    st.html(
        f"""<div class="learn-panel">
            <h2>薄弱点追踪</h2>
            <p>知识点</p><div class="learn-tag-row">{topics or '<span class="learn-tag">等待学习记录</span>'}</div>
            <p style="margin-top:14px;">关联课程</p><div class="learn-tag-row">{courses or '<span class="learn-tag">等待课程关联</span>'}</div>
            <p style="margin-top:14px;">常见错误</p><div class="learn-tag-row">{errors or '<span class="learn-tag">暂无错误模式</span>'}</div>
        </div>"""
    )


def _sanitized_conv_title(conv: dict[str, Any]) -> str:
    """Return a safe conversation title, replacing code-like titles with a generic label."""
    title = str(conv.get("title", "")).strip()
    if not title or title in {"新建代码对话", "未命名代码对话"}:
        return "代码学习对话"
    if _looks_like_code(title):
        return "代码学习对话"
    return title


def render_recent_activity(profile: dict[str, Any], code_conversations: list[dict[str, Any]]) -> None:
    """Show recent learning activity using metadata summaries — never raw user questions."""
    recent = profile.get("activity", {}).get("recent_tasks", [])[:5]
    lines = []
    for item in recent:
        if not isinstance(item, dict):
            continue
        label = _task_label(item)
        detail = _task_detail(item)
        lines.append(
            f"""<div class="learn-task">
                <strong>{html.escape(label)}</strong>
                <span>{html.escape(detail)}</span>
            </div>"""
        )
    if not lines:
        for conv in code_conversations[:4]:
            title = _sanitized_conv_title(conv)
            ts = str(conv.get("updated_at", ""))
            lines.append(
                f"""<div class="learn-task">
                    <strong>{html.escape(title)}</strong>
                    <span>{html.escape(ts)}</span>
                </div>"""
            )
    st.html(
        f'<div class="learn-panel"><h2>最近学习记录</h2>{"".join(lines) or "<p>暂无记录，先去代码学习 AI 问一个问题。</p>"}</div>'
    )


def render_map_actions() -> None:
    with st.container(border=True):
        st.markdown("#### 地图维护")
        st.caption("当课程资料或知识库更新后，可重新生成学习地图。")
        if st.button("重建学习地图", use_container_width=True):
            data = build_learning_map()
            save_learning_map(data)
            st.success("学习地图已重建")
            st.rerun()


def load_code_conversations() -> list[dict[str, Any]]:
    if not CODE_CONVERSATIONS_FILE.exists():
        return []
    try:
        data = json.loads(CODE_CONVERSATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _tag_markup(items: list[Any]) -> str:
    tags = []
    for item in items[:10]:
        if isinstance(item, dict):
            label = str(item.get("name", ""))
            count = item.get("count")
            if count:
                label = f"{label} ×{count}"
        else:
            label = str(item)
        if label:
            tags.append(f'<span class="learn-tag">{html.escape(label)}</span>')
    return "".join(tags)


def main() -> None:
    render_learning_dashboard_page()


if __name__ == "__main__":
    main()
