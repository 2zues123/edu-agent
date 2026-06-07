from __future__ import annotations

import json
from pathlib import Path


CONVERSATIONS_FILE = Path(".chat_history/conversations.json")


def normalize_conversation(conversation: dict) -> dict:
    conversation.setdefault("messages", [])
    conversation.setdefault("created_at", "")
    conversation.setdefault("updated_at", conversation.get("created_at", ""))
    conversation.setdefault("title", "未命名教务对话")
    conversation.setdefault("pinned", False)
    return conversation


def load_conversations() -> list[dict]:
    if not CONVERSATIONS_FILE.exists():
        return []
    try:
        data = json.loads(CONVERSATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [normalize_conversation(item) for item in data if isinstance(item, dict)]


def conversation_timestamp(conversation: dict) -> float:
    value = conversation.get("updated_at") or conversation.get("created_at") or ""
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError):
        return 0.0


def visible_conversations(conversations: list[dict]) -> list[dict]:
    return sorted(
        conversations,
        key=lambda item: (bool(item.get("pinned")), conversation_timestamp(item)),
        reverse=True,
    )
