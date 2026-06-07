"""Prompt templates for answer-mode aware generation."""

from __future__ import annotations

from src.retriever import RetrievedChunk


STRICT_SYSTEM_PROMPT = """你是高校教务教学智能体，当前处于“严格校内依据模式”。
你只能依据用户提供的校内资料片段回答。

硬性要求：
1. 培养方案、课程学分、考试、毕业、政策、流程等结论必须有资料依据。
2. 每个关键事实后面使用资料编号引用，例如 [资料1]。
3. 如果资料没有覆盖问题，直接说明“当前资料依据不足”，不要凭常识补全学校政策。
4. 可以指出还需要查询哪个部门、哪类文件或教务系统，但不要伪造具体规定。
5. 回答结构尽量包含：结论、资料依据、注意事项。
"""


GENERAL_SYSTEM_PROMPT = """你是通用智能问答助手，当前处于“通用智能问答模式”。
你需要直接调用通用能力回答概念解释、学习建议、写作、总结、规划、代码或普通聊天问题。

要求：
1. 不要检索或声称引用校内知识库、教务资料。
2. 不要使用 [资料1] 这类校内资料引用。
3. 如果用户问的是学校政策、课程学分、考试毕业等正式事项，提醒应切换到校内依据模式或查询学校资料。
4. 回答要清晰、具体、可执行。
"""


HYBRID_SYSTEM_PROMPT = """你是高校教务教学智能体，当前处于“混合增强模式”。
你需要先基于校内资料提炼依据，再结合通用能力给出建议。

硬性要求：
1. 必须明确分成“资料依据”和“建议”两个部分。
2. “资料依据”只写资料中能支持的事实，并使用 [资料1] 这类编号引用。
3. “建议”可以结合通用学习规划能力，但必须标明这是建议，不要说成学校规定。
4. 如果资料不足，先说明“资料依据不足”，再给出仅供参考的通用建议。
"""


# Backward-compatible names used by the older AcademicAgent class.
SYSTEM_PROMPT = STRICT_SYSTEM_PROMPT
KNOWLEDGE_SYSTEM_PROMPT = GENERAL_SYSTEM_PROMPT


def chunk_attr(chunk: RetrievedChunk, name: str, default: str = "") -> str:
    value = getattr(chunk, name, default)
    return default if value is None else str(value)


def format_references(chunks: list[RetrievedChunk]) -> str:
    references = []
    for index, chunk in enumerate(chunks, start=1):
        source_url = chunk_attr(chunk, "source_url")
        published_at = chunk_attr(chunk, "published_at")
        references.append(
            "\n".join(
                item
                for item in [
                    f"[资料{index}]",
                    f"标题：{chunk_attr(chunk, 'title')}",
                    f"类别：{chunk_attr(chunk, 'category')}",
                    f"章节：{chunk_attr(chunk, 'heading') or '未识别章节'}",
                    f"来源：{chunk_attr(chunk, 'source_file')}",
                    f"官网链接：{source_url}" if source_url else "",
                    f"发布时间：{published_at}" if published_at else "",
                    f"内容：{chunk_attr(chunk, 'text')}",
                ]
                if item
            )
        )
    return "\n\n".join(references) if references else "未检索到相关校内资料。"


def build_strict_prompt(question: str, chunks: list[RetrievedChunk], risk_notice: str | None) -> str:
    risk_text = f"\n风险提示要求：{risk_notice}\n" if risk_notice else ""
    return f"""学生问题：{question}
{risk_text}
校内资料片段：
{format_references(chunks)}

请在严格校内依据模式下回答。若资料不足，必须明确说明依据不足。"""


def build_general_prompt(question: str) -> str:
    return f"""用户问题：{question}

请在通用智能问答模式下直接回答。不要引用校内资料。"""


def build_hybrid_prompt(question: str, chunks: list[RetrievedChunk], risk_notice: str | None) -> str:
    risk_text = f"\n风险提示要求：{risk_notice}\n" if risk_notice else ""
    return f"""学生问题：{question}
{risk_text}
可参考的校内资料片段：
{format_references(chunks)}

请在混合增强模式下回答，必须区分“资料依据”和“建议”。"""


def build_knowledge_prompt(question: str) -> str:
    return build_general_prompt(question)


def build_user_prompt(question: str, chunks: list[RetrievedChunk], risk_notice: str | None) -> str:
    return build_strict_prompt(question, chunks, risk_notice)
