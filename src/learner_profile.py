"""Local learner profile for the Software College growth agent."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.learning_map import LearningSignal, signal_to_dict


LEARNER_PROFILE_FILE = Path(".chat_history/learner_profile.json")
MAX_RECENT_ITEMS = 20


DEFAULT_PROFILE: dict[str, Any] = {
    "basic": {
        "grade": "未设置",
        "goal": "课程补弱与代码能力提升",
        "direction": "软件工程综合能力",
    },
    "knowledge_state": {
        "weak_topics": [],
        "mastered_topics": [],
        "related_courses": [],
    },
    "coding_state": {
        "languages": [],
        "error_patterns": [],
        "skill_scores": {
            "编程基础": 35,
            "数据结构": 30,
            "算法设计": 28,
            "代码调试": 32,
            "工程实践": 26,
            "人工智能": 22,
            "课程政策理解": 40,
        },
    },
    "activity": {
        "recent_questions": [],
        "recent_tasks": [],
        "recent_signals": [],
    },
    "updated_at": "",
}


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_profile(path: Path = LEARNER_PROFILE_FILE) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return normalize_profile(data)
        except (OSError, json.JSONDecodeError):
            pass
    profile = normalize_profile({})
    save_profile(profile, path)
    return profile


def save_profile(profile: dict[str, Any], path: Path = LEARNER_PROFILE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile["updated_at"] = now_text()
    path.write_text(json.dumps(normalize_profile(profile), ensure_ascii=False, indent=2), encoding="utf-8")


def update_profile_from_signal(
    question: str,
    signal: LearningSignal | dict[str, Any],
    *,
    answer: str = "",
    language: str | None = None,
    path: Path = LEARNER_PROFILE_FILE,
) -> dict[str, Any]:
    profile = load_profile(path)
    payload = signal_to_dict(signal) if isinstance(signal, LearningSignal) else dict(signal)

    _merge_weighted_list(profile["knowledge_state"], "weak_topics", payload.get("topics", []))
    _merge_weighted_list(profile["knowledge_state"], "related_courses", payload.get("related_courses", []))
    _merge_weighted_list(profile["coding_state"], "error_patterns", payload.get("error_patterns", []))
    if language:
        _merge_weighted_list(profile["coding_state"], "languages", [language])

    skills = payload.get("skills", [])
    _bump_skill_scores(profile, skills, payload.get("difficulty", "入门"))

    task = {
        "question": _compact(question, 80),
        "topics": payload.get("topics", []),
        "skills": skills,
        "difficulty": payload.get("difficulty", "入门"),
        "related_courses": payload.get("related_courses", []),
        "next_exercises": payload.get("next_exercises", []),
        "created_at": now_text(),
    }
    _prepend_limited(profile["activity"], "recent_questions", _compact(question, 120))
    _prepend_limited(profile["activity"], "recent_tasks", task)
    _prepend_limited(profile["activity"], "recent_signals", payload)

    save_profile(profile, path)
    return profile


def update_basic_profile(*, grade: str, goal: str, direction: str, path: Path = LEARNER_PROFILE_FILE) -> dict[str, Any]:
    profile = load_profile(path)
    profile["basic"] = {
        "grade": grade.strip() or "未设置",
        "goal": goal.strip() or "课程补弱与代码能力提升",
        "direction": direction.strip() or "软件工程综合能力",
    }
    save_profile(profile, path)
    return profile


def recommended_tasks(profile: dict[str, Any], limit: int = 6) -> list[dict[str, str]]:
    weak_topics = _names(profile["knowledge_state"].get("weak_topics", []))
    courses = _names(profile["knowledge_state"].get("related_courses", []))
    errors = _names(profile["coding_state"].get("error_patterns", []))
    goal = str(profile.get("basic", {}).get("goal", "课程补弱与代码能力提升"))

    tasks: list[dict[str, str]] = []
    if weak_topics:
        tasks.append({
            "title": f"补强 {weak_topics[0]}",
            "detail": f"围绕 {weak_topics[0]} 做 2 道小题，并写出自己的解题步骤。",
            "tag": "知识点",
        })
    if courses:
        tasks.append({
            "title": f"回看 {courses[0]} 相关资料",
            "detail": f"把最近的代码问题和 {courses[0]} 中的概念对应起来。",
            "tag": "课程",
        })
    if errors:
        tasks.append({
            "title": f"整理 {errors[0]} 排错清单",
            "detail": "把触发条件、检查顺序、修复方式写成三列表格。",
            "tag": "Debug",
        })
    if "考研" in goal:
        tasks.append({"title": "算法基础专项", "detail": "本周完成递归、二分、动态规划各 1 道题。", "tag": "考研"})
    elif "竞赛" in goal:
        tasks.append({"title": "限时算法训练", "detail": "选择一个中等题，限制 35 分钟完成并复盘。", "tag": "竞赛"})
    elif "就业" in goal:
        tasks.append({"title": "项目代码复盘", "detail": "挑一段项目代码说明模块职责、边界条件和测试点。", "tag": "就业"})
    else:
        tasks.append({"title": "学习复盘", "detail": "总结最近 3 个问题背后的共同薄弱点。", "tag": "成长"})

    tasks.append({"title": "生成下一组练习", "detail": "在代码学习 AI 中输入“根据我的薄弱点出 3 道练习”。", "tag": "闭环"})
    return tasks[:limit]


def normalize_profile(data: dict[str, Any]) -> dict[str, Any]:
    profile = json.loads(json.dumps(DEFAULT_PROFILE, ensure_ascii=False))
    _deep_update(profile, data)
    profile.setdefault("updated_at", "")
    return profile


def _deep_update(base: dict[str, Any], update: dict[str, Any]) -> None:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _merge_weighted_list(section: dict[str, Any], key: str, names: list[str]) -> None:
    current = section.get(key, [])
    counter: Counter[str] = Counter()
    for item in current:
        if isinstance(item, dict):
            counter[str(item.get("name", ""))] += int(item.get("count", 1) or 1)
        elif item:
            counter[str(item)] += 1
    for name in names:
        if name:
            counter[str(name)] += 1
    section[key] = [
        {"name": name, "count": count}
        for name, count in counter.most_common(12)
        if name
    ]


def _bump_skill_scores(profile: dict[str, Any], skills: list[str], difficulty: str) -> None:
    scores = profile["coding_state"].setdefault("skill_scores", {})
    increment = {"入门": 4, "中等": 6, "进阶": 8}.get(str(difficulty), 4)
    for skill in skills:
        current = int(scores.get(skill, 25) or 25)
        scores[skill] = max(5, min(95, current + increment))


def _prepend_limited(section: dict[str, Any], key: str, item: Any) -> None:
    values = section.get(key, [])
    if not isinstance(values, list):
        values = []
    values.insert(0, item)
    section[key] = values[:MAX_RECENT_ITEMS]


def _compact(text: str, limit: int) -> str:
    compact = " ".join(str(text).split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _names(items: list[Any]) -> list[str]:
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
        else:
            name = str(item).strip()
        if name:
            names.append(name)
    return names
