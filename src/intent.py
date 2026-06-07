"""Rule-based intent classification for the education agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    category: str | None
    description: str


INTENTS = {
    "program": Intent("program", "programs", "培养方案、毕业要求、学分结构、课程模块相关问题"),
    "course": Intent("course", "courses", "课程大纲、课程内容、学分、考核方式、先修课程相关问题"),
    "workflow": Intent("workflow", "workflows", "办事流程、申请材料、办理步骤、入口指引相关问题"),
    "policy": Intent("policy", "policies", "学籍、考试、成绩、补考、重修、毕业、制度政策相关问题"),
    "knowledge": Intent("knowledge", None, "概念解释、学习建议、写作总结、代码规划等通用问题"),
    "general": Intent("general", None, "普通聊天或开放式通用问题"),
}


KEYWORDS = {
    "workflow": [
        "申请", "流程", "材料", "入口", "办理", "提交", "审批", "手续", "证明", "表格",
        "怎么申请", "如何办理", "在哪里办", "在哪办理",
    ],
    "policy": [
        "挂科", "补考", "重修", "成绩", "处分", "违纪", "休学", "复学", "退学", "学籍",
        "考试", "缓考", "免修", "毕业", "学位", "政策", "规定", "办法", "制度",
    ],
    "program": [
        "培养方案", "毕业要求", "学分要求", "总学分", "模块", "必修", "选修", "专业方向",
        "专业培养", "课程体系", "实践环节", "毕业设计",
    ],
    "course": [
        "课程", "学分", "先修", "考核", "考试方式", "学时", "教学内容", "教学大纲",
        "机器学习", "智能推荐", "人工智能导论", "科学计算", "经典模型", "数字图像处理",
    ],
}


STRICT_SCHOOL_TERMS = {
    "培养方案", "毕业", "学分", "课程", "考试", "考核", "成绩", "补考", "重修", "学籍",
    "流程", "申请", "政策", "规定", "办法", "制度", "学位", "毕业设计", "实践环节",
}

FORMAL_SCHOOL_TERMS = STRICT_SCHOOL_TERMS - {"课程"}
COURSE_FORMAL_TERMS = {
    "学分", "先修", "考核", "考试方式", "学时", "教学内容", "教学大纲", "课程大纲",
    "大纲", "开课", "课程号", "课程代码", "必修", "选修",
}

GENERAL_PATTERNS = [
    "什么是", "讲一下", "介绍一下", "解释一下", "说明一下", "原理", "概念", "定义",
    "区别", "为什么", "如何理解", "帮我写", "帮我总结", "写一段", "润色", "代码",
    "python", "java", "规划一下", "学习建议", "复习建议", "怎么学", "如何学习",
    "学习路线", "学习方法", "普通聊天",
]


def classify_intent(question: str) -> Intent:
    text = question.strip()

    # School policy and academic-affairs terms win over generic "what is" phrasing.
    if "学分" in text and any(word in text for word in KEYWORDS["course"]):
        return INTENTS["course"]

    if any(pattern in text for pattern in GENERAL_PATTERNS) and not any(term in text for term in FORMAL_SCHOOL_TERMS):
        return INTENTS["knowledge"]

    scores: dict[str, int] = {}
    for intent_name, words in KEYWORDS.items():
        scores[intent_name] = sum(1 for word in words if word in text)

    best_name, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        if best_name == "course" and not any(term in text for term in COURSE_FORMAL_TERMS):
            if any(pattern in text for pattern in GENERAL_PATTERNS):
                return INTENTS["knowledge"]
        return INTENTS[best_name]

    if any(term in text for term in STRICT_SCHOOL_TERMS):
        return INTENTS["policy"]

    return INTENTS["general"]
