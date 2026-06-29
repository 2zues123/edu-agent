"""Code Learning AI Agent — text Q&A (DeepSeek) + image recognition (Kimi vision)."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

from src.code_prompts import (
    CODE_LEARNING_SYSTEM_PROMPT,
    build_code_image_answer_prompt,
    build_code_image_recognition_prompt,
    build_code_text_prompt,
)
from src.learning_map import analyze_learning_signal

SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class CodeAgentAnswer:
    """Result returned by the Code Learning Agent."""

    question: str
    answer: str
    recognized_code: str | None = None
    language: str | None = None
    has_image: bool = False
    topics: list[str] | None = None
    skills: list[str] | None = None
    difficulty: str = "入门"
    related_courses: list[str] | None = None
    next_exercises: list[str] | None = None
    error_patterns: list[str] | None = None

    def learning_signal(self) -> dict:
        return {
            "topics": self.topics or [],
            "skills": self.skills or [],
            "difficulty": self.difficulty,
            "related_courses": self.related_courses or [],
            "next_exercises": self.next_exercises or [],
            "error_patterns": self.error_patterns or [],
        }


class CodeLearningAgent:
    """Agent for code learning Q&A — text via DeepSeek, vision via Kimi."""

    def __init__(self) -> None:
        load_dotenv()

        # Text model — DeepSeek
        self.text_api_key = (
            os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        self.text_base_url = (
            os.getenv("DEEPSEEK_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.deepseek.com"
        )
        self.text_model = (
            os.getenv("CODE_TEXT_MODEL")
            or os.getenv("DEEPSEEK_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "deepseek-chat"
        )

        # Vision model — Kimi (supports multimodal)
        self.vision_api_key = (
            os.getenv("CODE_VISION_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        self.vision_base_url = (
            os.getenv("CODE_VISION_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.moonshot.cn/v1"
        )
        self.vision_model = os.getenv("CODE_VISION_MODEL") or "moonshot-v1-8k-vision-preview"

        self._text_client: OpenAI | None = None
        self._vision_client: OpenAI | None = None

    @property
    def text_client(self) -> OpenAI:
        if self._text_client is None:
            if not self.text_api_key:
                raise RuntimeError("Missing DEEPSEEK_API_KEY or OPENAI_API_KEY in .env")
            self._text_client = OpenAI(
                api_key=self.text_api_key,
                base_url=self.text_base_url,
            )
        return self._text_client

    @property
    def vision_client(self) -> OpenAI:
        if self._vision_client is None:
            if not self.vision_api_key:
                raise RuntimeError("Missing CODE_VISION_API_KEY or OPENAI_API_KEY in .env — required for image recognition")
            self._vision_client = OpenAI(
                api_key=self.vision_api_key,
                base_url=self.vision_base_url,
            )
        return self._vision_client

    @property
    def has_vision(self) -> bool:
        """Check whether the vision API key is configured."""
        return bool(self.vision_api_key)

    # ── Text code Q&A ──────────────────────────────────────

    def answer_text_question(
        self,
        question: str,
        *,
        code_context: str = "",
        chat_history: list[dict[str, str]] | None = None,
    ) -> CodeAgentAnswer:
        """Answer a text-based code learning question using DeepSeek.

        Args:
            question: The user's question or code snippet.
            code_context: Optional additional code context.
            chat_history: Recent conversation messages for multi-turn context.
        """
        messages: list[dict] = [
            {"role": "system", "content": CODE_LEARNING_SYSTEM_PROMPT},
        ]
        if chat_history:
            for m in chat_history[-8:]:  # last 8 messages (4 turns)
                role = m.get("role", "user")
                content = str(m.get("content", ""))
                if role in ("user", "assistant") and content.strip():
                    messages.append({"role": role, "content": content})

        user_prompt = (
            build_code_text_prompt(question, code_context)
            + "\n\n请额外给出「关联课程」和「下一步练习」两个小节，"
              "把代码问题对应到软件工程专业课程或能力点。"
        )
        messages.append({"role": "user", "content": user_prompt})

        response = self.text_client.chat.completions.create(
            model=self.text_model,
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
        )
        answer = response.choices[0].message.content or ""
        language = _guess_language(question)
        signal = analyze_learning_signal(question, answer)
        return CodeAgentAnswer(
            question=question,
            answer=answer,
            language=language,
            topics=signal.topics,
            skills=signal.skills,
            difficulty=signal.difficulty,
            related_courses=signal.related_courses,
            next_exercises=signal.next_exercises,
            error_patterns=signal.error_patterns,
            has_image=False,
        )

    # ── Image recognition (Kimi vision) ────────────────────

    def recognize_code_image(self, image_bytes: bytes, mime_type: str) -> str:
        """Recognize code from an image screenshot using Kimi vision."""
        if mime_type not in SUPPORTED_IMAGE_TYPES:
            raise ValueError(
                f"Unsupported image type: {mime_type}. "
                f"Supported types: {', '.join(SUPPORTED_IMAGE_TYPES)}"
            )

        if not self.has_vision:
            raise RuntimeError("需要配置视觉模型 API Key（CODE_VISION_API_KEY）才能使用图片识别功能。")

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{image_b64}"

        prompt = build_code_image_recognition_prompt()
        response = self.vision_client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    def answer_with_image(
        self,
        question: str,
        image_bytes: bytes,
        mime_type: str,
        *,
        chat_history: list[dict[str, str]] | None = None,
    ) -> CodeAgentAnswer:
        """Recognize code from an image (Kimi), then answer (DeepSeek).

        Two-step process:
        1. Kimi vision model recognizes code from the image.
        2. DeepSeek text model answers based on the recognized code.
        """
        # Step 1: Recognize code from image (Kimi)
        recognized = self.recognize_code_image(image_bytes, mime_type)

        # Step 2: Answer question using text model (DeepSeek) with chat history
        messages: list[dict] = [
            {"role": "system", "content": CODE_LEARNING_SYSTEM_PROMPT},
        ]
        if chat_history:
            for m in chat_history[-8:]:
                role = m.get("role", "user")
                content = str(m.get("content", ""))
                if role in ("user", "assistant") and content.strip():
                    messages.append({"role": role, "content": content})

        text_prompt = (
            build_code_image_answer_prompt(question, recognized)
            + "\n\n请额外给出「关联课程」和「下一步练习」两个小节，"
              "把截图中的代码对应到软件工程专业课程或能力点。"
        )
        messages.append({"role": "user", "content": text_prompt})

        response = self.text_client.chat.completions.create(
            model=self.text_model,
            messages=messages,
            temperature=0.2,
            max_tokens=4096,
        )
        answer = response.choices[0].message.content or ""

        language = _guess_language(recognized)
        signal = analyze_learning_signal(f"{question}\n{recognized}", answer)

        return CodeAgentAnswer(
            question=question,
            answer=answer,
            recognized_code=recognized,
            language=language,
            has_image=True,
            topics=signal.topics,
            skills=signal.skills,
            difficulty=signal.difficulty,
            related_courses=signal.related_courses,
            next_exercises=signal.next_exercises,
            error_patterns=signal.error_patterns,
        )


# ── Helpers ──────────────────────────────────────────────────

def validate_image_upload(
    image_bytes: bytes,
    filename: str,
) -> tuple[bool, str]:
    """Validate an uploaded image file."""
    size_mb = len(image_bytes) / (1024 * 1024)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return False, f"图片大小 {size_mb:.1f}MB 超过限制（最大 5MB），请压缩后重试。"

    ext = os.path.splitext(filename)[1].lower()
    mime = EXT_TO_MIME.get(ext)
    if mime is None:
        return False, f"不支持的文件格式 {ext}，请上传 PNG、JPG、JPEG 或 WebP 格式的图片。"

    return True, ""


def _guess_language(code: str) -> str | None:
    """Simple heuristic to guess the programming language from code text."""
    code_lower = code.lower()
    if "def " in code and ("import " in code or "print(" in code or "class " in code):
        return "Python"
    if "public class " in code or "system.out.print" in code_lower:
        return "Java"
    if "#include" in code and ("std::" in code or "cout" in code_lower or "cin" in code_lower):
        return "C++"
    if "func " in code and ("package " in code or "fmt." in code):
        return "Go"
    if "fn " in code and ("let " in code or "mut " in code):
        return "Rust"
    if "function " in code or "const " in code and "=>" in code:
        return "JavaScript/TypeScript"
    if "import " in code:
        return "Python"
    if "#include" in code:
        return "C/C++"
    return None
