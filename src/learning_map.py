"""Learning map utilities for the Software College growth agent."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.retriever import DEFAULT_CHUNKS_FILE


LEARNING_MAP_FILE = Path("data/processed/learning_map.json")


COURSE_PATTERNS = [
    re.compile(r"([\u4e00-\u9fffA-Za-z0-9（）()·+\-]{2,24}(?:课程|导论|基础|实践|设计|工程|系统|算法|结构|模型|计算|学习|处理))"),
    re.compile(r"课程名称[：:\s]+([\u4e00-\u9fffA-Za-z0-9（）()·+\-]{2,24})"),
]


SKILL_RULES: dict[str, list[str]] = {
    "编程基础": ["程序设计", "Python", "Java", "C++", "语法", "函数", "类", "对象", "面向对象"],
    "数据结构": ["数据结构", "链表", "栈", "队列", "树", "图", "哈希", "堆"],
    "算法设计": ["算法", "复杂度", "递归", "动态规划", "贪心", "搜索", "排序", "二分", "回溯"],
    "代码调试": ["debug", "Debug", "报错", "异常", "错误", "调试", "IndexError", "TypeError"],
    "工程实践": ["软件工程", "项目", "实践", "需求", "测试", "设计模式", "架构", "Git"],
    "人工智能": ["人工智能", "机器学习", "深度学习", "神经网络", "模型", "推荐", "图像处理"],
    "课程政策理解": ["培养方案", "学分", "毕业", "必修", "选修", "课程大纲", "考核"],
}


TOPIC_RULES: dict[str, list[str]] = {
    "Python": ["Python", "def ", "print(", "列表", "字典"],
    "Java": ["Java", "public class", "System.out"],
    "C/C++": ["C++", "#include", "指针", "引用"],
    "递归": ["递归", "recursion"],
    "动态规划": ["动态规划", "DP", "状态转移"],
    "二分查找": ["二分", "binary_search", "binary search"],
    "复杂度分析": ["复杂度", "时间复杂度", "空间复杂度", "O("],
    "异常处理": ["异常", "报错", "Error", "Exception"],
    "面向对象": ["类", "对象", "继承", "封装", "多态"],
    "机器学习": ["机器学习", "训练", "模型", "分类", "回归"],
    "数字图像处理": ["图像", "卷积", "滤波", "像素", "边缘"],
    "软件工程实践": ["需求", "测试", "设计模式", "项目管理"],
}


@dataclass(frozen=True)
class LearningSignal:
    topics: list[str]
    skills: list[str]
    related_courses: list[str]
    difficulty: str
    next_exercises: list[str]
    error_patterns: list[str]


def load_learning_map(path: Path = LEARNING_MAP_FILE) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return ensure_learning_map_shape(data)
        except (OSError, json.JSONDecodeError):
            pass
    return build_learning_map()


def save_learning_map(data: dict[str, Any], path: Path = LEARNING_MAP_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ensure_learning_map_shape(data), ensure_ascii=False, indent=2), encoding="utf-8")


def build_learning_map(chunks_file: Path = DEFAULT_CHUNKS_FILE) -> dict[str, Any]:
    chunks = _read_chunks(chunks_file)
    course_counter: Counter[str] = Counter()
    course_sources: defaultdict[str, set[str]] = defaultdict(set)
    topic_counter: Counter[str] = Counter()
    skill_counter: Counter[str] = Counter()
    relations: set[tuple[str, str, str]] = set()

    for chunk in chunks:
        text = " ".join(
            str(chunk.get(key, ""))
            for key in ("title", "heading", "text", "source_file", "category")
        )
        source = str(chunk.get("source_file", "")) or str(chunk.get("title", ""))

        courses = infer_courses(text)
        topics = infer_topics(text)
        skills = infer_skills(text)

        for course in courses:
            course_counter[course] += 1
            if source:
                course_sources[course].add(source)
        for topic in topics:
            topic_counter[topic] += 1
        for skill in skills:
            skill_counter[skill] += 1

        for course in courses:
            for topic in topics:
                relations.add(("course_topic", course, topic))
            for skill in skills:
                relations.add(("course_skill", course, skill))
        for topic in topics:
            for skill in skills:
                relations.add(("topic_skill", topic, skill))

    if not course_counter:
        defaults = ["程序设计", "数据结构", "算法设计", "软件工程", "机器学习", "数字图像处理"]
        course_counter.update(defaults)

    courses_payload = [
        {
            "name": name,
            "weight": count,
            "source_files": sorted(course_sources.get(name, []))[:5],
            "type": infer_course_type(name),
        }
        for name, count in course_counter.most_common(40)
    ]
    topics_payload = [
        {"name": name, "weight": count, "keywords": TOPIC_RULES.get(name, [])[:6]}
        for name, count in topic_counter.most_common(60)
    ]
    skills_payload = [
        {"name": name, "weight": count, "keywords": SKILL_RULES.get(name, [])[:8]}
        for name, count in skill_counter.most_common()
    ]

    data = {
        "courses": courses_payload,
        "topics": topics_payload,
        "skills": skills_payload,
        "relations": [
            {"type": item[0], "source": item[1], "target": item[2]}
            for item in sorted(relations)
        ],
        "built_from": str(chunks_file),
    }
    return ensure_learning_map_shape(data)


def analyze_learning_signal(question: str, answer: str = "", *, learning_map: dict[str, Any] | None = None) -> LearningSignal:
    text = f"{question}\n{answer}"
    data = learning_map or load_learning_map()
    topics = infer_topics(text)
    skills = infer_skills(text)
    error_patterns = infer_error_patterns(text)
    related_courses = infer_related_courses(text, data, topics, skills)
    difficulty = infer_difficulty(text, topics, skills)
    next_exercises = build_next_exercises(topics, skills, difficulty)
    return LearningSignal(
        topics=topics,
        skills=skills,
        related_courses=related_courses,
        difficulty=difficulty,
        next_exercises=next_exercises,
        error_patterns=error_patterns,
    )


def signal_to_dict(signal: LearningSignal) -> dict[str, Any]:
    return {
        "topics": signal.topics,
        "skills": signal.skills,
        "related_courses": signal.related_courses,
        "difficulty": signal.difficulty,
        "next_exercises": signal.next_exercises,
        "error_patterns": signal.error_patterns,
    }


def infer_courses(text: str) -> list[str]:
    found: list[str] = []
    for pattern in COURSE_PATTERNS:
        for match in pattern.findall(text):
            course = clean_name(match)
            if 2 <= len(course) <= 24 and not _looks_like_noise(course):
                found.append(course)
    for keyword in ("程序设计", "数据结构", "算法设计", "软件工程", "机器学习", "人工智能导论", "数字图像处理", "科学计算", "智能推荐"):
        if keyword in text:
            found.append(keyword)
    return unique(found)[:8]


def infer_topics(text: str) -> list[str]:
    topics = [
        topic
        for topic, keywords in TOPIC_RULES.items()
        if any(keyword in text for keyword in keywords)
    ]
    return unique(topics)[:10]


def infer_skills(text: str) -> list[str]:
    skills = [
        skill
        for skill, keywords in SKILL_RULES.items()
        if any(keyword in text for keyword in keywords)
    ]
    return unique(skills)[:8]


def infer_related_courses(text: str, learning_map: dict[str, Any], topics: list[str], skills: list[str]) -> list[str]:
    direct = infer_courses(text)
    if direct:
        return direct[:5]

    relations = learning_map.get("relations", [])
    score: Counter[str] = Counter()
    targets = set(topics + skills)
    for rel in relations:
        if rel.get("type") in {"course_topic", "course_skill"} and rel.get("target") in targets:
            score[str(rel.get("source", ""))] += 1
    if score:
        return [name for name, _ in score.most_common(5) if name]

    fallback = []
    if "算法设计" in skills or any(t in topics for t in ("动态规划", "二分查找", "递归", "复杂度分析")):
        fallback.extend(["数据结构", "算法设计"])
    if "代码调试" in skills:
        fallback.append("程序设计")
    if "人工智能" in skills:
        fallback.extend(["机器学习", "人工智能导论"])
    if "工程实践" in skills:
        fallback.append("软件工程")
    return unique(fallback)[:5]


def infer_error_patterns(text: str) -> list[str]:
    patterns = {
        "数组/索引越界": ["IndexError", "越界", "out of range", "数组下标"],
        "类型不匹配": ["TypeError", "类型", "unsupported operand"],
        "空值/未初始化": ["None", "null", "空指针", "未初始化"],
        "语法错误": ["SyntaxError", "语法", "Syntax"],
        "循环边界错误": ["while", "for", "边界", "死循环"],
        "复杂度过高": ["超时", "TLE", "复杂度", "性能"],
    }
    return [name for name, keywords in patterns.items() if any(keyword in text for keyword in keywords)][:6]


def infer_difficulty(text: str, topics: list[str], skills: list[str]) -> str:
    if any(word in text for word in ("项目", "架构", "设计模式", "神经网络", "动态规划", "复杂度优化")):
        return "进阶"
    if any(topic in topics for topic in ("动态规划", "递归", "机器学习", "软件工程实践")):
        return "进阶"
    if any(skill in skills for skill in ("算法设计", "工程实践", "人工智能")):
        return "中等"
    return "入门"


def build_next_exercises(topics: list[str], skills: list[str], difficulty: str) -> list[str]:
    exercises: list[str] = []
    if "二分查找" in topics:
        exercises.append("写出二分查找的左右闭区间版本，并解释循环终止条件。")
    if "动态规划" in topics:
        exercises.append("为一个一维 DP 问题写出状态定义、转移方程和初始化。")
    if "递归" in topics:
        exercises.append("画出一次递归调用树，标出递归出口和返回值。")
    if "异常处理" in topics or "代码调试" in skills:
        exercises.append("根据报错信息列出 3 个可能原因，并逐一用静态检查排除。")
    if "复杂度分析" in topics or "算法设计" in skills:
        exercises.append("分析当前算法的时间复杂度，并尝试提出一个优化方向。")
    if not exercises:
        exercises.append("用自己的话复述本次问题涉及的核心知识点，并写一个 10 行以内的小例子。")
    if difficulty == "进阶":
        exercises.append("把本题改造成一个边界条件更多的变式题，并说明测试用例。")
    return unique(exercises)[:4]


def ensure_learning_map_shape(data: dict[str, Any]) -> dict[str, Any]:
    data.setdefault("courses", [])
    data.setdefault("topics", [])
    data.setdefault("skills", [])
    data.setdefault("relations", [])
    data.setdefault("built_from", str(DEFAULT_CHUNKS_FILE))
    return data


def _read_chunks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    chunks: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    item = json.loads(line)
                    if isinstance(item, dict):
                        chunks.append(item)
    except (OSError, json.JSONDecodeError):
        return []
    return chunks


def clean_name(value: str) -> str:
    return re.sub(r"[\s，。；：:、]+$", "", str(value).strip())


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = clean_name(item)
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def infer_course_type(name: str) -> str:
    if any(word in name for word in ("实践", "设计", "项目", "工程")):
        return "实践/工程"
    if any(word in name for word in ("机器学习", "人工智能", "图像", "推荐")):
        return "AI/智能"
    if any(word in name for word in ("算法", "结构", "程序")):
        return "编程/算法"
    return "专业课程"


def _looks_like_noise(value: str) -> bool:
    blocked = ("本课程", "该课程", "课程目标", "课程内容", "课程考核", "课程设计")
    return value in blocked or value.startswith("课程")
