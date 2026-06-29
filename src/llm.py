"""DeepSeek chat model factory — reads keys from st.secrets (Cloud) or .env (local)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def _env(key: str, default: str = "") -> str:
    """Read a config value: st.secrets first (Streamlit Cloud), then os.getenv (local .env)."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


def build_deepseek_chat() -> ChatOpenAI:
    load_dotenv()
    api_key = _env("DEEPSEEK_API_KEY") or _env("OPENAI_API_KEY")
    base_url = _env("DEEPSEEK_BASE_URL") or _env("OPENAI_BASE_URL") or "https://api.deepseek.com"
    model = _env("DEEPSEEK_MODEL") or _env("OPENAI_MODEL") or "deepseek-chat"

    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY — set in .streamlit/secrets.toml or .env")

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.2,
    )
