"""Learning dashboard — semester-based course browser powered by structured course DB.

Core feature: browse courses by semester (1-8), click any course to instantly
ask about it in the教务问答.  This turns the dashboard from a static report
into an interactive learning tool.
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

import streamlit as st

from src.course_db import CourseDB
from src.learner_profile import update_basic_profile
from src.student_memory import build_student_profile, generate_learning_advice, profile_to_llm_context
from src.ui.design_system import apply_design_system, inject_extra_css
from src.ui.layout import render_top_nav


CONVERSATIONS_FILE = Path(".chat_history/conversations.json")
BUILD_REPORT_FILE = Path("data/processed/build_report.json")

DASHBOARD_CSS = """
.dash-semester-nav {
    display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0;
}
.dash-semester-nav a {
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 60px; height: 36px; padding: 0 12px;
    border-radius: 10px; border: 1px solid var(--border);
    background: #fff; color: var(--ink); font-weight: 650; font-size: 0.84rem;
    text-decoration: none; transition: all 120ms;
}
.dash-semester-nav a.active, .dash-semester-nav a:hover {
    background: #168C8C; color: #fff; border-color: #168C8C;
}
.dash-course-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 12px 0;
}
.dash-course-card {
    border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px;
    background: #fff; transition: box-shadow 150ms;
}
.dash-course-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.dash-course-name { font-weight: 700; color: var(--ink); margin-bottom: 4px; }
.dash-course-meta { font-size: 0.76rem; color: var(--ink-muted); }
.dash-course-actions { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }

.dash-kpi-row {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px;
}
.dash-kpi {
    border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px;
    background: rgba(255,255,255,0.6);
}
.dash-kpi-label { color: var(--ink-muted); font-size: 0.78rem; font-weight: 700; }
.dash-kpi-value { color: var(--ink); font-size: 1.5rem; font-weight: 820; margin-top: 4px; }
.dash-kpi-sub { color: var(--ink-secondary); font-size: 0.76rem; margin-top: 2px; }

@media (max-width: 860px) {
    .dash-course-grid { grid-template-columns: 1fr; }
    .dash-kpi-row { grid-template-columns: 1fr; }
}

.dash-sem-badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700; margin-left: 6px; vertical-align: middle;
}
.dash-sem-badge.past { background: #E8F5E9; color: #2E7D32; }
.dash-sem-badge.current { background: #168C8C; color: #fff; }
.dash-sem-badge.future { background: #F5F5F5; color: #9E9E9E; }

.dash-grade-banner {
    background: linear-gradient(135deg, #E8F5E9 0%, #DDEAE2 100%);
    border: 1px solid rgba(22, 140, 140, 0.18);
    border-radius: 12px; padding: 12px 18px; margin-bottom: 16px;
    color: #17324A; font-size: 0.88rem; line-height: 1.6;
}
.dash-grade-banner strong { color: #168C8C; }

"""


def _load_kb_stats() -> dict:
    if not BUILD_REPORT_FILE.exists():
        return {"documents": 0, "chunks": 0, "built_at": ""}
    try:
        r = json.loads(BUILD_REPORT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"documents": 0, "chunks": 0, "built_at": ""}
    return {
        "documents": r.get("document_count", 0),
        "chunks": r.get("chunk_count", 0),
        "built_at": (r.get("built_at") or "")[:10],
    }


def _ask_about_course(course_name: str, question: str) -> None:
    """Navigate to chat view with a pre-filled question about a course."""
    st.session_state["pending_question"] = question
    st.query_params["view"] = "chat"
    st.query_params["stage"] = "start"
    st.rerun()


def render_learning_dashboard_page() -> None:
    apply_design_system()
    inject_extra_css(DASHBOARD_CSS)
    render_top_nav("learn")

    db = CourseDB()
    stats = _load_kb_stats()

    st.markdown("## 学习驾驶舱")
    st.caption("按学期浏览软件工程专业全部课程，点击即可查询详情")

    # ── Student profile + AI advice ──
    profile = build_student_profile()

    with st.expander("学习画像 & AI 建议", expanded=True):
        pcol1, pcol2 = st.columns([1, 2])
        with pcol1:
            basic = profile.get("basic", {})
            pstats = profile.get("stats", {})
            st.markdown("#### 基本信息")

            # Editable grade selector
            current_grade = basic.get("grade", "未设置")
            grade_options = ["未设置", "大一", "大二", "大三", "大四"]
            try:
                default_idx = grade_options.index(current_grade) if current_grade in grade_options else 0
            except ValueError:
                default_idx = 0
            new_grade = st.selectbox(
                "年级", grade_options, index=default_idx,
                key="profile_grade", label_visibility="collapsed",
            )
            if new_grade != current_grade:
                # Persist to learner_profile.json
                try:
                    update_basic_profile(
                        grade=new_grade,
                        goal=basic.get("goal", "课程补弱与代码能力提升"),
                        direction=basic.get("direction", "软件工程综合能力"),
                    )
                    st.rerun()
                except Exception:
                    pass

            st.caption(f"目标：{basic.get('goal', '未设置')}")
            st.caption(f"方向：{basic.get('direction', '未设置')}")
            st.markdown("#### 学习数据")
            st.caption(f"总提问：{pstats.get('total_questions', 0)} 次")
            st.caption(f"教务问答：{pstats.get('教务_questions', 0)} 次")
            st.caption(f"代码学习：{pstats.get('代码_questions', 0)} 次")
            st.caption(f"最近活跃：{pstats.get('last_active', '暂无')}")

            courses_mentioned = profile.get("courses_mentioned", [])
            if courses_mentioned:
                st.markdown("#### 关注课程")
                for name, count in courses_mentioned[:8]:
                    st.caption(f"· {name}（{count}次）")

            topics_engaged = profile.get("topics_engaged", [])
            if topics_engaged:
                st.markdown("#### 涉及主题")
                for name, count in topics_engaged[:6]:
                    st.caption(f"· {name}（{count}次）")

        with pcol2:
            advice = generate_learning_advice(profile)
            st.markdown(advice)

            if st.button("生成 AI 深度分析", use_container_width=True):
                with st.spinner("AI 正在分析你的学习情况..."):
                    try:
                        from src.llm import build_deepseek_chat
                        from langchain_core.messages import HumanMessage, SystemMessage
                        llm = build_deepseek_chat()
                        ctx = profile_to_llm_context(profile)
                        prompt = (
                            f"{ctx}\n"
                            "请根据以上学生画像，给出个性化的学习建议和课程规划方案。\n"
                            "要求：\n"
                            "1. 分析学生的学习特点和关注领域\n"
                            "2. 给出下学期的课程选择建议\n"
                            "3. 指出需要加强的知识领域\n"
                            "4. 语气亲切、具体、可执行\n"
                            "格式：用 Markdown，分「学习分析」「课程建议」「能力提升」三部分。"
                        )
                        response = llm.invoke([
                            SystemMessage(content="你是河北师范大学软件学院的学习导师，"
                                "根据学生的学习数据提供专业、个性化的学业指导。"),
                            HumanMessage(content=prompt),
                        ])
                        st.session_state["ai_advice"] = str(response.content)
                    except Exception as e:
                        st.session_state["ai_advice"] = f"AI 分析暂时不可用：{e}"

            if st.session_state.get("ai_advice"):
                st.markdown("---")
                st.markdown("### AI 深度分析")
                st.markdown(st.session_state["ai_advice"])

    # ── KPI row ──
    courses_with_sem = [c for c in db.courses if c.get("semester") and str(c["semester"]).strip().isdigit()]
    semesters_found = sorted(set(int(str(c["semester"])) for c in courses_with_sem))

    st.html(
        f"""<div class="dash-kpi-row">
            <div class="dash-kpi">
                <div class="dash-kpi-label">课程总数</div>
                <div class="dash-kpi-value">{len(db.courses)}</div>
                <div class="dash-kpi-sub">{len(db.by_type)} 个类别 · 覆盖 {len(semesters_found)} 个学期</div>
            </div>
            <div class="dash-kpi">
                <div class="dash-kpi-label">知识库</div>
                <div class="dash-kpi-value">{stats['documents']}</div>
                <div class="dash-kpi-sub">{stats['chunks']} 片段 · BGE 语义索引</div>
            </div>
            <div class="dash-kpi">
                <div class="dash-kpi-label">培养方案</div>
                <div class="dash-kpi-value">5</div>
                <div class="dash-kpi-sub">2019-2025级 · 6份文档</div>
            </div>
        </div>"""
    )

    # ── Grade-to-semester context ──
    GRADE_MAP = {"大一": 1, "大二": 2, "大三": 3, "大四": 4}
    grade_num = GRADE_MAP.get(current_grade, 0)  # 0 if not set
    if grade_num:
        completed_end = (grade_num - 1) * 2
        current_start = completed_end + 1
        current_end = min(grade_num * 2, 8)
        future_start = current_end + 1

        sem_status: dict[int, str] = {}
        for s in range(1, 9):
            if s <= completed_end:
                sem_status[s] = "past"
            elif s <= current_end:
                sem_status[s] = "current"
            else:
                sem_status[s] = "future"

        # Banner showing grade context
        completed_label = f"第1-{completed_end}学期" if completed_end > 0 else "无"
        current_label = f"第{current_start}-{current_end}学期" if current_start <= current_end else "无"
        future_label = f"第{future_start}-8学期" if future_start <= 8 else "无"
        st.html(
            f"""<div class="dash-grade-banner">
                <strong>{current_grade}</strong> |
                已完成：{completed_label} |
                当前学期：{current_label} |
                未修：{future_label}
            </div>"""
        )
    else:
        sem_status = {s: "future" for s in range(1, 9)}

    # ── Semester tabs ──
    STATUS_LABEL = {"past": "[已完成]", "current": "[当前学期]", "future": "[未开始]"}
    STATUS_BADGE = {"past": "past", "current": "current", "future": "future"}

    all_semesters = list(range(1, 9))
    tab_labels = [
        f"第{s}学期 {STATUS_LABEL.get(sem_status[s], '')}" for s in all_semesters
    ]
    tabs = st.tabs(tab_labels)

    for sem, tab in zip(all_semesters, tabs):
        with tab:
            sem_courses = [c for c in db.courses
                           if c.get("semester") and str(c["semester"]).strip().isdigit()
                           and int(str(c["semester"])) == sem]

            status = sem_status.get(sem, "future")
            if status == "current" and grade_num:
                st.caption(f"当前学期 | {len(sem_courses)} 门课程")
            elif status == "past" and grade_num:
                st.caption(f"已完成学期 | {len(sem_courses)} 门课程")
            elif not sem_courses:
                st.caption("该学期暂无课程数据")
                continue
            else:
                st.caption(f"{len(sem_courses)} 门课程")

            # Group by type
            by_type: dict[str, list[dict]] = defaultdict(list)
            for c in sem_courses:
                by_type[c.get("course_type", "其他")].append(c)

            for ctype, courses in sorted(by_type.items()):
                st.markdown(f"**{ctype}**")
                cols = st.columns(3)
                for i, c in enumerate(courses):
                    with cols[i % 3]:
                        with st.container(border=True):
                            name = c["name"]
                            meta_parts = []
                            if c.get("credits") is not None:
                                meta_parts.append(f"{c['credits']}学分")
                            if c.get("hours_total") is not None:
                                meta_parts.append(f"{c['hours_total']}学时")
                            req = c.get("required", "")
                            if req:
                                meta_parts.append(req)
                            meta = " · ".join(meta_parts) if meta_parts else ""

                            st.markdown(f"**{html.escape(name)}**")
                            if meta:
                                st.caption(meta)

                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("查详情", key=f"detail_{c['code']}", use_container_width=True):
                                    st.session_state["pending_question"] = f"{name}多少学分？考核方式是什么？"
                                    st.query_params["view"] = "chat"
                                    st.rerun()
                            with c2:
                                if st.button("大纲", key=f"syllabus_{c['code']}", use_container_width=True):
                                    st.session_state["pending_question"] = f"{name}的教学大纲和教学内容是什么？"
                                    st.query_params["view"] = "chat"
                                    st.rerun()

    # ── Footer: all courses by type (quick reference) ──
    st.markdown("---")
    st.markdown("### 按类别浏览")

    cols = st.columns(3)
    for i, (ctype, names) in enumerate(sorted(db.by_type.items(), key=lambda x: -len(x[1]))):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{ctype}**（{len(names)}门）")
                for name in names[:6]:
                    st.caption(f"· {html.escape(name)}")
                if len(names) > 6:
                    st.caption(f"…还有 {len(names) - 6} 门")

    st.caption(
        f"数据来源：软件工程专业培养方案（2019-2025级）· "
        f"知识库 {stats['documents']} 文档 · {stats['chunks']} 片段"
    )


def main() -> None:
    render_learning_dashboard_page()


if __name__ == "__main__":
    main()
