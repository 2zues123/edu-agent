"""Student memory system — builds a learning profile from conversation history.

Reads all chat histories (教务问答 + 代码学习), extracts mentioned courses
and topics, and generates a structured profile.  This profile is:
  1. Shown on the learning dashboard as "学习画像"
  2. Fed to the LLM for personalized answers
  3. Used to generate AI learning advice
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

CONVERSATIONS_FILE = Path(".chat_history/conversations.json")
CODE_CONVERSATIONS_FILE = Path(".chat_history/code_conversations.json")
LEARNER_PROFILE_FILE = Path(".chat_history/learner_profile.json")

# Course names from intent.py — used to detect course mentions in questions
COURSE_NAMES = [
    "C语言", "C程序设计", "C++", "Java", "Java程序设计", "Python",
    "Web开发", "Web前端", "前端开发", "后端开发",
    "数据结构", "操作系统", "计算机组成", "计算机网络", "数据库",
    "数据库原理", "编译原理", "软件工程", "软件工程概论",
    "软件测试", "软件测试基础", "算法", "算法设计", "程序设计",
    "高等数学", "线性代数", "概率论", "概率统计", "数理统计",
    "离散数学", "数值分析", "数学分析", "复变函数", "数学建模",
    "大学英语", "大学物理", "大学体育", "思政", "马原",
    "毛概", "思修", "近代史", "形势与政策",
    "机器学习", "人工智能导论", "智能推荐", "数字图像处理",
    "科学计算", "经典模型", "深度学习", "自然语言处理",
]

TOPIC_KEYWORDS = {
    "编程基础": ["Python", "Java", "C语言", "函数", "变量", "循环", "条件", "数组", "字符串"],
    "数据结构": ["链表", "栈", "队列", "树", "图", "哈希", "堆", "排序"],
    "算法设计": ["算法", "复杂度", "递归", "动态规划", "贪心", "二分", "回溯"],
    "代码调试": ["debug", "报错", "异常", "错误", "调试", "bug"],
    "工程实践": ["项目", "需求", "测试", "设计模式", "架构", "Git"],
    "人工智能": ["机器学习", "深度学习", "神经网络", "模型", "训练", "AI"],
    "学分政策": ["学分", "必修", "选修", "毕业", "补考", "重修", "绩点"],
    "培养方案": ["培养方案", "课程体系", "教学计划", "第几学期", "开课"],
    "考试考核": ["考试", "考核", "平时成绩", "期末", "闭卷", "开卷"],
    "选课流程": ["选课", "退课", "申请", "转专业", "缓考"],
}


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _extract_questions(conversations: list[dict]) -> list[str]:
    """Extract all user questions from conversation histories."""
    questions = []
    for conv in conversations:
        for msg in conv.get("messages", []):
            if msg.get("role") == "user":
                content = str(msg.get("content", "")).strip()
                if content and len(content) > 1:
                    questions.append(content)
    return questions


def build_student_profile() -> dict:
    """Build a student learning profile from all conversation histories."""
    # Load all conversations
    jw_convs = _load_json(CONVERSATIONS_FILE)
    code_convs = _load_json(CODE_CONVERSATIONS_FILE)

    jw_questions = _extract_questions(jw_convs)
    code_questions = _extract_questions(code_convs)
    all_questions = jw_questions + code_questions

    # Extract mentioned courses
    course_counter: Counter[str] = Counter()
    for q in all_questions:
        for cn in COURSE_NAMES:
            if cn in q:
                course_counter[cn] += 1

    # Extract topics
    topic_counter: Counter[str] = Counter()
    for q in all_questions:
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                topic_counter[topic] += 1

    # Load manual profile
    basic = {"grade": "未设置", "goal": "课程补弱与代码能力提升", "direction": "软件工程综合能力"}
    if LEARNER_PROFILE_FILE.exists():
        try:
            p = json.loads(LEARNER_PROFILE_FILE.read_text(encoding="utf-8"))
            basic = p.get("basic", basic)
        except Exception:
            pass

    # Recent activity timestamps
    latest_ts = ""
    for conv in jw_convs + code_convs:
        ts = conv.get("updated_at", "") or conv.get("created_at", "")
        if ts > latest_ts:
            latest_ts = ts

    return {
        "basic": basic,
        "stats": {
            "total_questions": len(all_questions),
            "教务_questions": len(jw_questions),
            "代码_questions": len(code_questions),
            "教务_conversations": len(jw_convs),
            "代码_conversations": len(code_convs),
            "last_active": latest_ts or "暂无记录",
        },
        "courses_mentioned": course_counter.most_common(15),
        "topics_engaged": topic_counter.most_common(10),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def profile_to_llm_context(profile: dict) -> str:
    """Convert a student profile into a context string for the LLM prompt."""
    basic = profile.get("basic", {})
    stats = profile.get("stats", {})
    courses = profile.get("courses_mentioned", [])
    topics = profile.get("topics_engaged", [])

    grade = basic.get("grade", "未设置")
    GRADE_MAP = {"大一": 1, "大二": 2, "大三": 3, "大四": 4}
    gn = GRADE_MAP.get(grade, 0)
    sem_info = ""
    if gn:
        sem_info = f"（当前学期：第{(gn-1)*2+1}-{min(gn*2, 8)}学期，已完成第1-{(gn-1)*2}学期）"
    parts = ["[学生画像]"]
    parts.append(f"年级：{grade}{sem_info}")
    parts.append(f"学习目标：{basic.get('goal', '未设置')}")
    parts.append(f"专业方向：{basic.get('direction', '未设置')}")
    parts.append(f"历史提问：{stats.get('total_questions', 0)} 次 "
                 f"（教务{stats.get('教务_questions', 0)} + "
                 f"代码{stats.get('代码_questions', 0)}）")

    if courses:
        parts.append("关注课程：" + "、".join(
            f"{name}({count}次)" for name, count in courses[:8]))

    if topics:
        parts.append("涉及主题：" + "、".join(
            f"{name}({count}次)" for name, count in topics[:6]))

    parts.append("")
    return "\n".join(parts)


def generate_learning_advice(profile: dict) -> str:
    """Generate personalized learning advice using the profile data.

    This is a rule-based summary shown immediately; the LLM-generated
    version is produced on-demand via the dashboard button.
    """
    basic = profile.get("basic", {})
    stats = profile.get("stats", {})
    courses = dict(profile.get("courses_mentioned", []))
    topics = dict(profile.get("topics_engaged", []))

    lines = []

    # 1. Overall status
    total = stats.get("total_questions", 0)
    if total == 0:
        return ("你还没有开始使用教务问答和代码学习功能。\n\n"
                "建议先从「教务问答」开始，尝试询问课程学分、培养方案等问题，"
                "系统会根据你的提问自动分析学习情况。")

    # Grade-aware context
    grade = basic.get("grade", "未设置")
    grade_hint = ""
    if grade in ("大一", "大二", "大三", "大四"):
        gn = {"大一": 1, "大二": 2, "大三": 3, "大四": 4}[grade]
        cs = (gn - 1) * 2 + 1
        ce = min(gn * 2, 8)
        grade_hint = f"，当前应为第{cs}-{ce}学期"
    lines.append(f"### 学习概况\n"
                 f"你已进行 {total} 次提问（教务 {stats.get('教务_questions', 0)} 次 + "
                 f"代码 {stats.get('代码_questions', 0)} 次），最近活跃于 {stats.get('last_active', '未知')}。年级：{grade}{grade_hint}。")

    # 2. Course focus
    if courses:
        top_courses = sorted(courses.items(), key=lambda x: -x[1])[:5]
        names = [f"{n}（{c}次）" for n, c in top_courses]
        lines.append(f"### 课程关注度\n你关注最多的课程是：{'、'.join(names)}。")

    # 3. Topic engagement
    if topics:
        top_topics = sorted(topics.items(), key=lambda x: -x[1])[:5]
        names = [f"{n}（{c}次）" for n, c in top_topics]
        lines.append(f"### 知识领域\n你的提问涉及：{'、'.join(names)}。")

    # 4. Suggestions based on patterns
    lines.append("### 建议")
    suggestions = []

    if total < 5:
        suggestions.append("你刚开始使用系统，建议多问一些课程相关问题（如'数据结构多少学分？'），系统会逐渐了解你的学习方向。")

    if courses:
        top_course = max(courses, key=courses.get)
        suggestions.append(f"你对「{top_course}」关注最多，可以在教务问答中进一步询问它的考核方式、先修课程和教学内容。")

    if topics:
        # Check for gaps
        if "编程基础" not in topics and stats.get("代码_questions", 0) > 0:
            suggestions.append("你的代码提问较多但编程基础相关话题较少，建议在代码学习中关注基础语法和数据结构。")
        if "学分政策" in topics:
            suggestions.append("你对学分政策有关注，建议在教务问答中系统了解培养方案和毕业要求。")

    if not courses and stats.get("教务_questions", 0) >= 3:
        suggestions.append("你的教务问题未涉及具体课程名，建议直接问'高等数学多少学分？'或'数据结构是必修吗？'来获得精确的课程信息。")

    # Grade-aware suggestions
    if grade in ("大一", "大二", "大三", "大四"):
        gn = {"大一": 1, "大二": 2, "大三": 3, "大四": 4}[grade]
        suggestions.append(
            f"作为{grade}学生，你正在学习第{(gn-1)*2+1}-{min(gn*2, 8)}学期的课程。"
            f"可以在学习驾驶舱中查看当前学期和过往学期的课程安排，确保不遗漏必修课。"
        )

    if not suggestions:
        suggestions.append("继续保持当前的学习节奏，定期回顾薄弱知识点。")

    for s in suggestions:
        lines.append(f"- {s}")

    return "\n\n".join(lines)
