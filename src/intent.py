"""Rule-based intent classification for the first Agent prototype."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    category: str | None
    description: str


INTENTS = {
    "program": Intent("program", "programs", "培养方案、毕业要求、学分、课程模块相关问题"),
    "course": Intent("course", "courses", "课程大纲、课程内容、考核方式、先修课程相关问题"),
    "workflow": Intent("workflow", "workflows", "办事流程、申请材料、办理步骤相关问题"),
    "policy": Intent("policy", "policies", "学籍、考试、成绩、补考重修等制度问题"),
    "knowledge": Intent("knowledge", None, "通用知识讲解、概念解释、原理说明类问题"),
    "general": Intent("general", None, "通用问题"),
}


KEYWORDS = {
    "workflow": ["申请", "流程", "材料", "入口", "办理", "怎么交", "怎么提交", "缓考"],
    "policy": ["挂科", "补考", "重修", "成绩", "处分", "违纪", "休学", "复学", "退学", "学籍"],
    "program": ["培养方案", "毕业", "学分", "模块", "必修", "选修", "专业方向", "毕业要求"],
    "course": ["课程", "先修", "考核", "考试方式", "学时", "教学内容", "教学大纲", "怎么学"],
}

COURSE_HINTS = [
    "课程",
    "先修",
    "考核",
    "考试方式",
    "教学内容",
    "教学大纲",
    "机器学习",
    "智能推荐",
    "人工智能导论",
    "科学计算",
    "经典模型",
    "数字图像处理",
]

KNOWLEDGE_PATTERNS = [
    "什么是",
    "讲一下",
    "介绍一下",
    "解释一下",
    "说明一下",
    "原理",
    "概念",
    "定义",
    "区别",
    "为什么",
    "如何理解",
]


def classify_intent(question: str) -> Intent:
    text = question.strip()
    if any(pattern in text for pattern in KNOWLEDGE_PATTERNS):
        return INTENTS["knowledge"]

    if "学分" in text and any(word in text for word in COURSE_HINTS):
        return INTENTS["course"]

    scores: dict[str, int] = {}
    for intent_name, words in KEYWORDS.items():
        scores[intent_name] = sum(1 for word in words if word in text)

    best_name, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        return INTENTS["general"]
    return INTENTS[best_name]
