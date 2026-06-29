"""Intent classification — keyword rules + semantic vector fallback.

Fast keyword matching handles the common unambiguous cases (学分, 补考,
培养方案, etc.).  When keywords don't match, the BGE embedding model
compares the query to each intent's description for semantic similarity.
This eliminates the need to constantly add new keywords for every query
pattern students invent.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    category: str | None
    description: str


INTENTS = {
    "program": Intent("program", "programs", "培养方案、毕业要求、学分结构、课程模块、专业方向、"
                       "开课学期、必修选修、通识课程、数学课英语课等课程设置、"
                       "学院领导、师资队伍、校区地址、联系方式等学院信息"),
    "course": Intent("course", "courses", "具体课程的名称、学分、学时、考核方式、先修课程、"
                      "教学内容、教学大纲、考试还是考查、第几学期开课"),
    "workflow": Intent("workflow", "workflows", "办事流程、申请材料、办理步骤、选课退课操作、"
                       "入口指引、表格下载、手续办理"),
    "policy": Intent("policy", "policies", "学籍管理、考试安排、补考重修、挂科处理、休学复学退学、"
                     "成绩管理、绩点计算、毕业学位、违纪处分、政策规定制度办法"),
    "knowledge": Intent("knowledge", None, "概念解释、学习建议、写作总结、代码编程规划、"
                        "原理定义、区别对比等通用知识问题"),
    "general": Intent("general", None, "普通聊天、开放式的非教务问题"),
}

# ── High-precision keyword rules ──────────────────────────
# These cover the most common unambiguous cases quickly without model inference.

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

STRONG_SIGNALS: dict[str, Intent] = {}

# Program-level signals → program intent
for _kw in ["培养方案", "总学分", "毕业要求", "课程体系", "教学计划",
             "专业方向", "专业培养", "实践环节", "毕业设计", "毕业论文",
             "第二课堂", "创新创业学分", "素质拓展", "课外学分",
             "数学课", "通识必修", "通识选修", "专业必修", "专业选修",
             "第几学期", "大几上", "大几学"]:
    STRONG_SIGNALS[_kw] = INTENTS["program"]

# Course-level signals → course intent
for _kw in ["学分", "学时", "先修", "考核方式", "考试方式", "教学大纲",
             "教学内容", "课程代码", "课程号", "周学时", "开课", "实验课",
             "考试课", "考查课"]:
    STRONG_SIGNALS[_kw] = INTENTS["course"]

# Policy signals → policy intent
for _kw in ["挂科", "补考", "重修", "缓考", "休学", "复学", "退学",
             "学籍", "处分", "违纪", "绩点", "GPA", "学分绩"]:
    STRONG_SIGNALS[_kw] = INTENTS["policy"]

# Workflow signals → workflow intent
for _kw in ["怎么申请", "如何办理", "在哪里办", "在哪办理", "选课系统",
             "怎么选课", "如何选课", "怎么退课",
             "缓考", "怎么缓考", "申请缓考"]:
    STRONG_SIGNALS[_kw] = INTENTS["workflow"]

# Calendar / schedule signals → policy intent
for _kw in ["校历", "暑假", "寒假", "开学", "放假", "什么时候开学"]:
    STRONG_SIGNALS[_kw] = INTENTS["policy"]

GENERAL_PATTERNS = [
    "什么是", "讲一下", "介绍一下", "解释一下", "说明一下",
    "区别", "为什么", "如何理解", "帮我写", "帮我总结", "写一段", "润色",
    "规划一下", "学习建议", "复习建议", "怎么学", "如何学习",
    "学习路线", "学习方法", "普通聊天",
]


# ── Semantic fallback (BGE embeddings) ────────────────────

_semantic_model = None
_intent_embeddings: dict[str, np.ndarray] = {}


def _get_semantic_model():
    """Lazy-load the BGE model (shared with embeddings module via cache)."""
    global _semantic_model
    if _semantic_model is not None:
        return _semantic_model
    # Try to reuse the cached model from embeddings module first
    try:
        from src.embeddings import _SENTENCE_TRANSFORMER_CACHE
        cache_key = "BAAI/bge-small-zh-v1.5:False"
        if cache_key in _SENTENCE_TRANSFORMER_CACHE:
            _semantic_model = _SENTENCE_TRANSFORMER_CACHE[cache_key]
            return _semantic_model
    except Exception:
        pass
    from sentence_transformers import SentenceTransformer
    _semantic_model = SentenceTransformer("BAAI/bge-small-zh-v1.5", local_files_only=True)
    return _semantic_model


def _get_intent_embeddings() -> dict[str, np.ndarray]:
    """Pre-compute embeddings for each intent description."""
    global _intent_embeddings
    if _intent_embeddings:
        return _intent_embeddings
    model = _get_semantic_model()
    names = list(INTENTS.keys())
    descriptions = [INTENTS[n].description for n in names]
    vectors = model.encode(descriptions, normalize_embeddings=True)
    _intent_embeddings = {name: vec for name, vec in zip(names, vectors)}
    return _intent_embeddings


def _semantic_classify(text: str) -> Intent:
    """Classify by comparing query embedding to each intent's description."""
    try:
        model = _get_semantic_model()
        q_vec = model.encode([text], normalize_embeddings=True)[0]
        ie = _get_intent_embeddings()

        best_name, best_score = "general", -1.0
        for name, vec in ie.items():
            sim = float(np.dot(q_vec, vec))
            if sim > best_score:
                best_score = sim
                best_name = name

        # Require minimum similarity threshold
        if best_score < 0.35:
            return INTENTS["general"]
        # knowledge vs general: require higher threshold for knowledge
        if best_name == "knowledge" and best_score < 0.45:
            return INTENTS["general"]
        return INTENTS[best_name]
    except Exception:
        return INTENTS["general"]


# ── Main classifier ───────────────────────────────────────

def classify_intent(question: str) -> Intent:
    text = question.strip()

    # ── Step 1: Strong keyword signals (high precision) ──
    for kw, intent in STRONG_SIGNALS.items():
        if kw in text:
            # If course name + general pattern → knowledge (e.g. "什么是机器学习")
            if intent == INTENTS["course"]:
                if any(p in text for p in ["什么是", "是什么"]) and not \
                   any(t in text for t in ["学分", "学时", "考核", "先修", "必修"]):
                    return INTENTS["knowledge"]
            return intent

    # Course name without formal terms: check context
    for cn in COURSE_NAMES:
        if cn in text:
            # Knowledge-like language with course name → knowledge
            if any(t in text for t in ["是什么", "什么是", "讲一下", "介绍一下",
                                         "解释", "说明", "帮我写", "代码"]):
                return INTENTS["knowledge"]
            if any(t in text for t in ["必修", "选修", "限选", "第几学期", "哪个学期",
                                         "什么时候上", "大几上", "大几学", "几个学期"]):
                return INTENTS["program"]
            if any(t in text for t in ["学分", "学时", "考核", "先修", "多少"]):
                return INTENTS["course"]
            # Bare course name → course intent
            return INTENTS["course"]

    # ── Step 2: General patterns → knowledge ──
    if any(p in text for p in GENERAL_PATTERNS):
        return INTENTS["knowledge"]

    # ── Step 3: Keyword scoring for remaining cases ──
    keyword_map = {
        "workflow": ["申请", "流程", "材料", "办理", "提交", "审批", "手续", "证明", "表格", "选课", "退课"],
        "policy": ["考试", "成绩", "毕业", "学位", "政策", "规定", "办法", "制度", "排名", "平均分"],
        "program": ["必修", "选修", "模块", "课程", "学期", "培养", "上几学期"],
    }
    scores = {name: sum(1 for w in words if w in text) for name, words in keyword_map.items()}
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return INTENTS[best]

    # ── Step 4: Semantic fallback (BGE) for everything else ──
    return _semantic_classify(text)
