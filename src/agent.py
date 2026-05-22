"""DeepSeek-backed academic affairs teaching Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.intent import Intent, classify_intent
from src.prompts import SYSTEM_PROMPT, build_user_prompt
from src.retriever import KeywordRetriever, RetrievedChunk
from src.risk import RISK_NOTICE, is_high_risk


@dataclass(frozen=True)
class AgentAnswer:
    question: str
    intent: Intent
    high_risk: bool
    answer: str
    sources: list[RetrievedChunk]


class AcademicAgent:
    def __init__(
        self,
        *,
        chunks_file: Path = Path("data/processed/chunks.jsonl"),
        model: str | None = None,
        use_llm: bool = True,
    ):
        load_dotenv()
        self.retriever = KeywordRetriever(chunks_file)
        self.model = model or os.getenv("DEEPSEEK_MODEL") or os.getenv("OPENAI_MODEL") or "deepseek-chat"
        self.use_llm = use_llm
        self.client = self._build_client() if use_llm else None

    def answer(self, question: str, *, top_k: int = 5) -> AgentAnswer:
        intent = classify_intent(question)
        high_risk = is_high_risk(question)
        sources = self.retriever.search(question, category=intent.category, top_k=top_k)
        if not sources and intent.category is not None:
            sources = self.retriever.search(question, category=None, top_k=top_k)

        risk_notice = RISK_NOTICE if high_risk else None
        if self.use_llm:
            answer = self._generate_answer(question, sources, risk_notice)
        else:
            answer = self._fallback_answer(question, sources, risk_notice)

        return AgentAnswer(
            question=question,
            intent=intent,
            high_risk=high_risk,
            answer=answer,
            sources=sources,
        )

    @staticmethod
    def _build_client() -> OpenAI:
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY or OPENAI_API_KEY in .env")
        if not base_url:
            base_url = "https://api.deepseek.com"
        return OpenAI(api_key=api_key, base_url=base_url)

    def _generate_answer(
        self,
        question: str,
        sources: list[RetrievedChunk],
        risk_notice: str | None,
    ) -> str:
        user_prompt = build_user_prompt(question, sources, risk_notice)
        response = self.client.chat.completions.create(  # type: ignore[union-attr]
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _fallback_answer(
        question: str,
        sources: list[RetrievedChunk],
        risk_notice: str | None,
    ) -> str:
        if not sources:
            return "当前知识库中没有检索到明确依据，建议咨询学院教务办公室。"

        lines = ["已检索到以下相关依据，可用于生成回答："]
        if risk_notice:
            lines.append(f"\n风险提示：{risk_notice}")
        for index, source in enumerate(sources, start=1):
            excerpt = source.text[:280].replace("\n", " ")
            lines.append(
                f"\n[资料{index}] {source.title}｜{source.heading or '未识别章节'}\n"
                f"来源：{source.source_file}\n"
                f"片段：{excerpt}"
            )
        return "\n".join(lines)

