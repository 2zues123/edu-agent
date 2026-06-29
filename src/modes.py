"""Answer mode routing for the education agent."""

from __future__ import annotations

from dataclasses import dataclass

from src.intent import Intent


@dataclass(frozen=True)
class AnswerMode:
    name: str
    label: str
    description: str
    use_retrieval: bool
    require_sources: bool


STRICT_MODE = AnswerMode(
    name="strict_rag",
    label="严格校内依据",
    description="用于培养方案、课程学分、考试、毕业、政策、流程等问题；必须检索并引用校内资料。",
    use_retrieval=True,
    require_sources=True,
)

GENERAL_MODE = AnswerMode(
    name="general_llm",
    label="通用智能问答",
    description="用于概念解释、学习建议、写作、总结、规划、代码、普通聊天等问题；不检索校内资料。",
    use_retrieval=False,
    require_sources=False,
)

HYBRID_MODE = AnswerMode(
    name="hybrid_enhanced",
    label="混合增强",
    description="用于结合学校资料给建议的问题；先检索资料，再区分资料依据和模型建议。",
    use_retrieval=True,
    require_sources=False,
)


SCHOOL_TERMS = [
    "学校", "校内", "学院", "专业", "培养方案", "课程", "学分", "毕业", "考试", "成绩",
    "政策", "流程", "教务", "河北师范大学", "河北师大", "软件工程",
]

ADVICE_TERMS = [
    "建议", "规划", "计划", "推荐", "怎么选", "如何安排", "适合", "提升", "准备",
    "路径", "方案", "帮我设计", "结合", "参考",
]

REFERENCE_TERMS = [
    "结合", "根据", "基于", "参考", "按照", "利用", "校内资料", "学校资料", "培养方案",
]

STRICT_INTENTS = {"program", "course", "workflow", "policy"}


def classify_answer_mode(question: str, intent: Intent) -> AnswerMode:
    text = question.strip()
    has_school_context = any(term in text for term in SCHOOL_TERMS)
    asks_for_advice = any(term in text for term in ADVICE_TERMS)
    asks_to_use_references = any(term in text for term in REFERENCE_TERMS)

    modern_school_terms = ["学校", "校内", "学院", "软件学院", "软件工程", "专业", "课程", "培养方案", "学分"]
    modern_advice_terms = ["怎么学", "如何学", "学习路径", "学习规划", "方向规划", "推荐", "适合", "提升", "补弱", "考研", "就业", "竞赛"]
    modern_reference_terms = ["结合", "根据", "基于", "参考", "按照", "课程体系", "培养方案"]
    has_school_context = has_school_context or any(term in text for term in modern_school_terms)
    asks_for_advice = asks_for_advice or any(term in text for term in modern_advice_terms)
    asks_to_use_references = asks_to_use_references or any(term in text for term in modern_reference_terms)

    if has_school_context and asks_for_advice and asks_to_use_references:
        return HYBRID_MODE

    if has_school_context and asks_for_advice:
        return HYBRID_MODE

    if intent.name in STRICT_INTENTS:
        return STRICT_MODE

    return GENERAL_MODE
