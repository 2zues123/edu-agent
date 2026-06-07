"""DeepSeek chat model factory."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def build_deepseek_chat() -> ChatOpenAI:
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.deepseek.com"
    model = os.getenv("DEEPSEEK_MODEL") or os.getenv("OPENAI_MODEL") or "deepseek-chat"

    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY or OPENAI_API_KEY in .env")

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.2,
    )

