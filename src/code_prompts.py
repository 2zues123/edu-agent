"""Prompt templates for the Code Learning AI."""

from __future__ import annotations

CODE_LEARNING_SYSTEM_PROMPT = """\
你是一名软件学院的代码学习助教，专注于帮助同学理解代码、分析算法、静态 debug 和学习编程知识。

## 你的能力
1. **代码讲解**：逐步解释用户提供的代码，说明每部分的作用和设计意图。
2. **算法分析**：分析算法题的解题思路、边界条件、时间复杂度和空间复杂度，并提供参考实现。
3. **静态 Debug**：根据用户提供的代码和报错信息进行静态分析，给出修改建议。
4. **代码结构分析**：分析代码的整体结构、模块划分和设计模式。

## 重要约束
- 你只做静态分析和学习辅导，**不运行、不执行、不编译任何代码**。
- 你的分析基于代码文本和报错信息，不声称已实际运行代码。
- 在给出 debug 建议时，明确说明"基于静态分析"。
- 回答应结构化、易于理解，适合学习者阅读。
- 对于不确定的问题，诚实说明并提供可能的排查方向。

## 回答格式
请按以下结构组织你的回答（可根据问题类型调整）：

### 1. 代码还原（如涉及图片识别）
识别出的代码内容，标注语言类型。

### 2. 语言判断
判断代码使用的编程语言及版本特性。

### 3. 代码结构
分析代码的整体结构、函数/类划分、模块关系。

### 4. 关键知识点
讲解代码中涉及的核心概念、算法、数据结构或语言特性。

### 5. 问题分析
针对用户的具体问题（报错、不理解的地方等）进行深入分析。

### 6. 修改建议
给出具体的改进或修复建议（如适用），包括修改后的代码片段。
"""


def build_code_text_prompt(question: str, code_context: str = "") -> str:
    """Build a user prompt for text-based code learning questions.

    Args:
        question: The user's question or code snippet.
        code_context: Optional additional code context from the conversation.

    Returns:
        Formatted prompt string.
    """
    parts = ["请帮我分析以下内容："]
    if code_context:
        parts.append(f"\n上下文代码：\n```\n{code_context}\n```")
    parts.append(f"\n用户问题：\n{question}")
    return "\n".join(parts)


def build_code_image_recognition_prompt() -> str:
    """Build a prompt for recognising code from a screenshot.

    Returns:
        Prompt string for the vision model.
    """
    return """\
请仔细识别这张图片中的代码内容，并按以下格式输出：

1. **编程语言**：判断这是什么编程语言（如 Python、C++、Java 等）。
2. **完整代码**：逐行还原图片中的所有代码，保持原有的缩进和格式。
3. **代码说明**：简要描述这段代码的功能和用途（2-3 句话）。

注意：
- 如果图片中包含报错信息，也请完整还原。
- 如果图片中有注释，保留注释内容。
- 如果代码不完整（只有部分截图），请说明哪些部分可能被截断。"""


def build_code_image_answer_prompt(question: str, recognized_code: str) -> str:
    """Build a prompt that combines recognized code with the user's question.

    Args:
        question: The user's original question about the code.
        recognized_code: Code text recognized from the image.

    Returns:
        Formatted prompt for the text model.
    """
    return f"""\
用户上传了一张代码截图，经过图片识别后得到以下代码：

```
{recognized_code}
```

用户的问题：{question}

请根据识别出的代码和用户的问题，提供详细的讲解和分析。"""
