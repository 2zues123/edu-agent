"""Structured course database — enables counting/listing queries.

Queries like "软件工程要学几门数学课？" cannot be answered by chunk-based
RAG alone because they require aggregating across multiple chunks.  This
module provides direct lookups against the extracted course DB.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

LEARNING_MAP_FILE = Path("data/processed/learning_map.json")


class CourseDB:
    def __init__(self, path: Path = LEARNING_MAP_FILE):
        self.path = path
        self.data = self._load()
        self.courses: list[dict] = self.data.get("courses", [])
        self.by_type: dict[str, list[str]] = self.data.get("course_types", {})

    def _load(self) -> dict:
        if not self.path.exists():
            return {"courses": [], "course_types": {}, "by_type": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def search(self, *, name: str = "", course_type: str = "",
               required: str = "", semester: str = "",
               keyword: str = "") -> list[dict]:
        """Flexible course search with multiple filters."""
        results = self.courses
        if name:
            results = [c for c in results if name in c.get("name", "")]
        if course_type:
            results = [c for c in results if c.get("course_type") == course_type]
        if required:
            results = [c for c in results if required in c.get("required", "")]
        if semester:
            results = [c for c in results if semester in str(c.get("semester", ""))]
        if keyword:
            results = [c for c in results if keyword in c.get("name", "")
                       or keyword in c.get("category", "")]
        return results

    def count_by_type(self, course_type: str) -> int:
        return len(self.by_type.get(course_type, []))

    def list_by_type(self, course_type: str) -> list[str]:
        return self.by_type.get(course_type, [])

    def get_course(self, name: str) -> dict | None:
        for c in self.courses:
            if name in c.get("name", "") or c.get("name", "") in name:
                return c
        return None


# ── Patterns for detecting counting / listing queries ──

COUNT_PATTERNS = [
    re.compile(r"(几门|多少门|几科|多少科|有几门)\s*(\w*)\s*(课|课程)"),
    re.compile(r"(\w+)\s*(课|课程)\s*(有几门|有多少|有哪些|有那些|有吗|有)"),
    re.compile(r"(有哪些|哪些是|什么是|那些是|那些)\s*(\w*)\s*(课|课程)"),
    re.compile(r"(\w+)\s*(要学|要上|需要|需要学|需要学习)\s*(几门|多少|几个|那些|哪些|什么|啥)"),
    re.compile(r"(\w+)\s*(课|课程).*(有|有哪些|有那些)"),
    re.compile(r"(什么|哪些|那些)\s*(\w+)\s*(课|课程)"),
]

TYPE_KEYWORDS = {
    "数学": "数学类",
    "数学课": "数学类",
    "英语": "英语类",
    "思政": "思政类",
    "体育": "体育类",
    "物理": "物理类",
    "编程": "编程语言类",
    "编程语言": "编程语言类",
    "专业课": "计算机核心",
    "专业基础课": "编程语言类",
    "专业必修": "计算机核心",
    "专业核心": "计算机核心",
    "计算机核心": "计算机核心",
    "核心课": "计算机核心",
    "专业选修": "其他",
    "通识": "思政类",  # will also match 英语/体育/物理
    "公共": "思政类",
    "AI": "AI/数据科学",
    "人工智能": "AI/数据科学",
    "实践": "实践/项目",
    "实训": "实践/项目",
    "项目": "实践/项目",
    "毕业": "实践/项目",
}


def is_counting_query(question: str) -> str:
    """Return the course type keyword if this is a counting/listing query, else ''."""
    for pattern in COUNT_PATTERNS:
        m = pattern.search(question)
        if m:
            # Extract the type keyword
            for g in m.groups():
                if g and g not in ("几门", "多少门", "几科", "多少科", "有几门",
                                    "有哪些", "哪些是", "什么是", "那些是", "那些",
                                    "哪些", "要学", "要上", "需要", "需要学", "需要学习",
                                    "课", "课程", "有几门", "有多少", "几个",
                                    "有", "有吗", "有那些", "什么", "啥"):
                    return g
            # If no specific type, it's a general counting query
            return "__all__"

    # Fallback: if regex didn't match but question directly mentions
    # a known course type, treat as a listing query for that type
    type_kw = _match_type_keyword(question)
    if type_kw:
        return type_kw

    return ""


def _match_type_keyword(question: str) -> str:
    """Check if question directly references a known course type category."""
    question_lower = question.lower()
    # Direct mapping from common query terms to course type names
    for kw, ctype in TYPE_KEYWORDS.items():
        if kw in question_lower:
            return kw
    return ""


def query_course_db(question: str) -> str | None:
    """Answer a course counting/listing query from the structured DB.

    Returns a formatted answer string, or None if this isn't a counting query.
    """
    type_keyword = is_counting_query(question)
    if not type_keyword:
        # Final fallback: check if question directly contains a TYPE_KEYWORDS key
        type_keyword = _match_type_keyword(question)
    if not type_keyword:
        # Also check if question mentions any course-related listing pattern
        if any(kw in question for kw in ["有什么课", "有哪些课", "哪些课程",
                                           "什么课程", "专业课", "课有", "课有?"]):
            type_keyword = "__all__"
        else:
            return None

    db = CourseDB()

    # Map keyword to course type
    # Strategy: check both (a) kw is substring of type_keyword, and
    # (b) type_keyword is substring of kw (e.g. "专业" matches "专业课")
    mapped_types: list[str] = []
    for kw, ctype in TYPE_KEYWORDS.items():
        if kw in type_keyword or type_keyword in kw:
            mapped_types.append(ctype)

    # Deduplicate
    mapped_types = list(dict.fromkeys(mapped_types))

    # "通识" / "公共" should expand to all general education types
    if any(kw in type_keyword for kw in ["通识", "公共必修", "公共"]):
        mapped_types = ["思政类", "英语类", "体育类", "物理类"]

    is_listing = any(kw in question for kw in [
        "有哪些", "哪些是", "那些", "哪些", "列表", "列出", "有吗",
        "有什么", "要学", "需要学", "需要学习", "有几门", "多少门",
    ])
    is_counting = any(kw in question for kw in ["几门", "多少门", "几科", "几个"])

    if type_keyword == "__all__" or (is_counting and not mapped_types):
        # General: return type summary
        lines = ["软件工程专业课程分类统计（来自培养方案）："]
        for ctype, names in sorted(db.by_type.items()):
            lines.append(f"  - {ctype}: {len(names)} 门")
        return "\n".join(lines)

    if mapped_types:
        all_names: list[str] = []
        # Also collect source docs for these courses
        all_sources: set[str] = set()
        for mt in mapped_types:
            for name in db.list_by_type(mt):
                all_names.append(name)
                course = db.get_course(name)
                if course and course.get("source"):
                    all_sources.add(course["source"])
        all_names = sorted(set(all_names))
        if not all_names:
            return f"未在培养方案中找到「{type_keyword}」类课程。"
        type_label = "、".join(mapped_types)
        source_note = f"\n（数据来源：{'、'.join(sorted(all_sources)[:3])}）" if all_sources else ""
        return f"软件工程专业{type_label}课程（共 {len(all_names)} 门）：{source_note}\n" + \
               "\n".join(f"  - {name}" for name in all_names)

    # Keyword search
    results = db.search(keyword=type_keyword)
    if results:
        names = sorted(set(c["name"] for c in results))
        return f"与「{type_keyword}」相关的课程（共 {len(names)} 门）：\n" + \
               "\n".join(f"  - {name}" for name in names)

    return None


def lookup_course_info(course_name: str) -> str | None:
    """Look up a specific course by name and return its structured info."""
    db = CourseDB()
    course = db.get_course(course_name)
    if not course:
        return None

    parts = [f"**{course['name']}**"]
    if course.get("code"):
        parts.append(f"  课程代码: {course['code']}")
    if course.get("credits") is not None:
        parts.append(f"  学分: {course['credits']}")
    if course.get("hours_total") is not None:
        parts.append(f"  总学时: {course['hours_total']}")
    if course.get("semester"):
        parts.append(f"  开课学期: {course['semester']}")
    if course.get("required"):
        parts.append(f"  课程性质: {course['required']}")
    if course.get("course_type"):
        parts.append(f"  课程类别: {course['course_type']}")
    parts.append(f"  来源: {course.get('source', '')}")
    return "\n".join(parts)
