"""Prompt templates for DeepSeek-backed answer generation."""

from __future__ import annotations

from src.retriever import RetrievedChunk


SYSTEM_PROMPT = """你是高校教务教学智能体。
你的任务是基于给定知识库片段回答学生问题。
要求：
1. 优先依据知识库，不要编造学校政策。
2. 政策、培养方案、考试成绩、毕业相关回答必须谨慎。
3. 如果依据不足，明确说明当前知识库没有足够依据。
4. 输出结构尽量包含：结论、依据、注意事项、后续建议。
5. 引用依据时使用资料编号，例如 [资料1]。
"""


def build_user_prompt(question: str, chunks: list[RetrievedChunk], risk_notice: str | None) -> str:
    references = []
    for index, chunk in enumerate(chunks, start=1):
        references.append(
            "\n".join(
                [
                    f"[资料{index}]",
                    f"标题：{chunk.title}",
                    f"类别：{chunk.category}",
                    f"章节：{chunk.heading or '未识别章节'}",
                    f"来源：{chunk.source_file}",
                    f"内容：{chunk.text}",
                ]
            )
        )

    risk_text = f"\n风险提示要求：{risk_notice}\n" if risk_notice else ""
    return f"""学生问题：{question}
{risk_text}
知识库片段：
{chr(10).join(references) if references else "未检索到相关资料。"}

请基于以上资料生成回答。"""

