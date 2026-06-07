from __future__ import annotations

import json
from pathlib import Path


def load_knowledge_summary() -> dict:
    report_file = Path("data/processed/build_report.json")
    chunks_file = Path("data/processed/chunks.jsonl")
    summary = {
        "documents": 0,
        "chunks": 0,
        "courses": 0,
        "programs": 0,
        "web_pages": 0,
        "attachments": 0,
        "built_at": "本地知识库",
    }

    if report_file.exists():
        try:
            report = json.loads(report_file.read_text(encoding="utf-8"))
            parsed = report.get("parsed", [])
            summary["documents"] = int(report.get("parsed_count") or report.get("document_count") or 0)
            summary["chunks"] = int(report.get("chunk_count") or 0)
            summary["courses"] = sum(1 for item in parsed if item.get("category") == "courses")
            summary["programs"] = sum(1 for item in parsed if item.get("category") == "programs")
            summary["web_pages"] = sum(1 for item in parsed if item.get("category") == "web")
            built_at = str(report.get("built_at") or "")
            if built_at:
                summary["built_at"] = built_at[:10]
        except (OSError, ValueError, TypeError):
            pass

    web_report_file = Path("data/processed/web_crawl_report.json")
    if web_report_file.exists():
        try:
            web_report = json.loads(web_report_file.read_text(encoding="utf-8"))
            summary["web_pages"] = int(web_report.get("page_count") or summary["web_pages"])
            summary["attachments"] = int(web_report.get("attachment_count") or 0)
            built_at = str(web_report.get("built_at") or "")
            if built_at:
                summary["built_at"] = built_at[:10]
        except (OSError, ValueError, TypeError):
            pass

    if not summary["chunks"] and chunks_file.exists():
        try:
            summary["chunks"] = sum(1 for line in chunks_file.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            pass

    return summary
