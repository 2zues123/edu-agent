#!/usr/bin/env python3
"""Systematic RAG gap analysis — tests common student queries and reports failures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.intent import classify_intent
from src.modes import classify_answer_mode
from src.retriever import HybridRetriever, RetrievedChunk

# ── Test queries organized by category ──

TEST_QUERIES = {
    "课程查询（具体课程）": [
        "C语言多少学分？",
        "数据结构是必修课吗？",
        "操作系统多少学分？",
        "数据库原理要学多久？",
        "计算机网络是考试课还是考查课？",
        "离散数学有先修要求吗？",
        "软件工程要学几门数学课？",
        "高等数学是多少学时？",
        "线性代数是第几学期上？",
        "大学英语要学几个学期？",
    ],
    "课程查询（已有大纲）": [
        "机器学习多少学分？",
        "人工智能导论考核方式是什么？",
        "智能推荐有什么先修课程？",
        "数字图像处理多少学时？",
        "科学计算是必修吗？",
        "经典模型教什么内容？",
    ],
    "培养方案/毕业": [
        "毕业需要多少总学分？",
        "第二课堂需要多少学分？",
        "实践环节包括哪些内容？",
        "毕业设计多少学分？",
        "创新创业学分怎么获得？",
        "大三上学期有哪些课？",
        "专业选修课要选够多少学分？",
        "通识必修课有哪些？",
    ],
    "考试/成绩": [
        "挂科了怎么办？",
        "补考什么时候报名？",
        "怎么查成绩？",
        "绩点怎么算的？",
        "缓考怎么申请？",
        "期末考试时间在哪看？",
        "重修要交钱吗？",
    ],
    "学籍/政策": [
        "转专业有什么条件？",
        "怎么办理休学？",
        "退学后还能复学吗？",
        "辅修学位有什么要求？",
    ],
    "选课/教务流程": [
        "怎么选课？",
        "选课系统在哪里？",
        "怎么退课？",
        "课表在哪里看？",
    ],
    "学期/校历": [
        "什么时候放暑假？",
        "下学期什么时候开学？",
        "校历在哪里看？",
    ],
    "学院信息": [
        "软件学院的院长是谁？",
        "软件学院在哪个校区？",
        "软件学院的教务办公室在哪？",
    ],
}

retriever = HybridRetriever()


def analyze_query(question: str, top_k: int = 5) -> dict:
    intent = classify_intent(question)
    mode = classify_answer_mode(question, intent)

    # Determine actual category used for search
    if intent and intent.category == "courses":
        search_category = None  # matches the node logic
    else:
        search_category = intent.category if intent else None

    results = retriever.search(question, category=search_category, top_k=top_k)

    # Fallback: if no results, try without category filter
    if not results and search_category is not None:
        results = retriever.search(question, category=None, top_k=top_k)

    return {
        "question": question,
        "intent": intent.name,
        "intent_category": intent.category,
        "mode": mode.name,
        "search_category": str(search_category),
        "result_count": len(results),
        "top_scores": [round(r.score, 2) for r in results[:3]],
        "top_titles": [r.title[:40] for r in results[:3]],
        "top_categories": [r.category for r in results[:3]],
        "has_relevant": _judge_relevance(question, results),
    }


def _judge_relevance(question: str, results: list[RetrievedChunk]) -> str:
    """Quick heuristic: does the top result look relevant?"""
    if not results:
        return "NO_RESULTS"
    best = results[0]
    best_text = (best.title + best.heading + best.text).lower()

    # Extract key terms from question
    q_terms = set()
    # Course names
    for term in ["c语言", "数据结构", "操作系统", "数据库", "计算机网络", "离散数学",
                  "高等数学", "线性代数", "大学英语", "机器学习", "人工智能导论",
                  "智能推荐", "数字图像处理", "科学计算", "经典模型"]:
        if term in question.lower():
            q_terms.add(term)

    # Topic terms
    for term in ["学分", "必修", "考核", "学时", "毕业", "补考", "重修", "转专业",
                  "选课", "缓考", "休学", "退学", "数学课", "实践", "通识",
                  "选修", "第二课堂", "创新创业", "绩点", "课表", "校历",
                  "暑假", "开学", "院长", "校区", "教务办公室"]:
        if term in question.lower():
            q_terms.add(term)

    if not q_terms:
        return "UNCERTAIN"

    matches = sum(1 for t in q_terms if t in best_text)
    if matches >= len(q_terms) * 0.5:
        return "LIKELY_OK"
    if matches > 0:
        return "PARTIAL"
    return "LIKELY_IRRELEVANT"


def main():
    print("=" * 70)
    print("RAG 教务问答系统 — 缺陷分析测试")
    print("=" * 70)

    total = 0
    no_results = []
    likely_irrelevant = []
    partial = []
    intent_gaps = []

    for group, queries in TEST_QUERIES.items():
        print(f"\n{'─' * 70}")
        print(f"📋 {group}")
        print(f"{'─' * 70}")
        for q in queries:
            total += 1
            result = analyze_query(q)
            relevance = result["has_relevant"]
            icon = {"LIKELY_OK": "✅", "PARTIAL": "⚠️", "LIKELY_IRRELEVANT": "❌",
                     "NO_RESULTS": "🚫", "UNCERTAIN": "❓"}.get(relevance, "❓")

            print(f"  {icon} {q}")
            print(f"     意图={result['intent']} 模式={result['mode']} "
                  f"检索数={result['result_count']} "
                  f"Top={result['top_titles'][:2]}")
            if relevance in ("NO_RESULTS",):
                no_results.append(q)
            elif relevance == "LIKELY_IRRELEVANT":
                likely_irrelevant.append(q)
            elif relevance == "PARTIAL":
                partial.append(q)

            # Intent gap: course queries classified as non-course
            if any(kw in q for kw in ["学分", "必修", "选修", "考核", "学时",
                                        "先修", "大纲", "考试课", "考查课"]):
                if result["intent"] not in ("course", "program"):
                    intent_gaps.append(f"{q} → {result['intent']} (should be course/program)")

    print("\n" + "=" * 70)
    print("📊 汇总")
    print("=" * 70)
    print(f"  测试问题总数: {total}")
    print(f"  🚫 零结果 (NO_RESULTS): {len(no_results)}")
    for q in no_results:
        print(f"     - {q}")
    print(f"  ❌ 可能不相关 (LIKELY_IRRELEVANT): {len(likely_irrelevant)}")
    for q in likely_irrelevant:
        print(f"     - {q}")
    print(f"  ⚠️ 部分相关 (PARTIAL): {len(partial)}")
    for q in partial:
        print(f"     - {q}")
    print(f"  🔀 意图分类偏差: {len(intent_gaps)}")
    for g in intent_gaps:
        print(f"     - {g}")

    # ── Structural analysis ──
    print("\n" + "=" * 70)
    print("📊 结构性问题")
    print("=" * 70)

    # Check data coverage
    chunks_file = Path("data/processed/chunks.jsonl")
    chunks = [json.loads(line) for line in chunks_file.open(encoding="utf-8") if line.strip()]

    categories = {}
    for c in chunks:
        cat = c.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    print(f"\n  知识库分块分布 ({len(chunks)} chunks):")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count} ({count/len(chunks)*100:.0f}%)")

    # course coverage
    course_chunks = [c for c in chunks if c.get("category") == "courses"]
    course_titles = set(c.get("title", "") for c in course_chunks)
    print(f"\n  已有课程大纲 ({len(course_titles)} 门):")
    for t in sorted(course_titles):
        print(f"    - {t}")

    # Program coverage
    program_chunks = [c for c in chunks if c.get("category") == "programs"]
    program_titles = set(c.get("title", "") for c in program_chunks)
    print(f"\n  已有培养方案 ({len(program_titles)} 份):")
    for t in sorted(program_titles):
        print(f"    - {t}")

    print(f"\n  缺失数据:")
    print(f"    - 2019级培养方案: .doc格式无法解析 (Windows无textutil)")
    print(f"    - 核心课程大纲 (C语言/数据结构/OS/DB/网络等): 0 份")
    print(f"    - 数学类课程大纲: 0 份")
    print(f"    - 英语类课程大纲: 0 份")
    print(f"    - 校历数据: 0 份")
    print(f"    - 选课系统说明: 0 份")

    # Policy coverage check
    policy_chunks = [c for c in chunks if c.get("category") == "policies"]
    print(f"\n  制度政策文档: {len(policy_chunks)} chunks "
          f"({len(set(c.get('title','') for c in policy_chunks))} 份)")
    # Check what policy topics are covered
    policy_text = " ".join(c.get("text", "") for c in policy_chunks)
    policy_topics = {
        "补考": "补考" in policy_text,
        "重修": "重修" in policy_text,
        "缓考": "缓考" in policy_text,
        "休学": "休学" in policy_text,
        "复学": "复学" in policy_text,
        "退学": "退学" in policy_text,
        "转专业": "转专业" in policy_text,
        "绩点": "绩点" in policy_text or "GPA" in policy_text,
        "第二课堂": "第二课堂" in policy_text,
        "创新创业": "创新创业" in policy_text,
        "辅修": "辅修" in policy_text,
        "学位": "学位" in policy_text,
    }
    print(f"  政策主题覆盖:")
    for topic, covered in policy_topics.items():
        print(f"    {'✅' if covered else '❌'} {topic}")

    # Web content quality
    web_chunks = [c for c in chunks if c.get("category") == "web"]
    web_short = [c for c in web_chunks if len(c.get("text", "")) < 300]
    print(f"\n  Web抓取质量: {len(web_chunks)} chunks, "
          f"{len(web_short)} 个内容<300字 (信息量不足)")

    # Intent classification gaps — formal test
    print(f"\n  意图分类盲区:")
    course_queries = ["C语言", "数据结构", "操作系统", "数据库原理", "计算机网络",
                       "离散数学", "高等数学", "线性代数", "大学英语", "大学物理",
                       "编译原理", "软件工程概论", "Java程序设计", "Web开发",
                       "几门数学课", "多少门数学", "数学课程"]
    for q in course_queries:
        intent = classify_intent(q)
        if intent.name not in ("course", "program"):
            print(f"    ❌ '{q}' → {intent.name} (应为 course/program)")

    # Check if "几门数学课" type queries can work
    print(f"\n  '几门数学课'类查询检索测试:")
    math_queries = ["软件工程要学几门数学课？", "有哪些数学课？", "数学类课程有哪些？"]
    for q in math_queries:
        results = retriever.search(q, category=None, top_k=5)
        titles = [r.title[:40] for r in results[:3]]
        print(f"    {q} → {titles}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
