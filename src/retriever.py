"""Retrievers over generated JSONL chunks and local vector indexes."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import faiss

from src.embeddings import build_embedding_provider_from_config


DEFAULT_CHUNKS_FILE = Path("data/processed/chunks.jsonl")
DEFAULT_FAISS_INDEX_FILE = Path("data/index/faiss/chunks.faiss")
DEFAULT_FAISS_METADATA_FILE = Path("data/index/faiss/metadata.jsonl")
DEFAULT_VECTORIZER_FILE = Path("data/index/faiss/vectorizer.pkl")
DEFAULT_FAISS_CONFIG_FILE = Path("data/index/faiss/index_config.json")


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    title: str
    category: str
    source_file: str
    heading: str
    text: str
    score: float
    source_url: str = ""
    site: str = ""
    published_at: str = ""


def load_chunks(path: Path = DEFAULT_CHUNKS_FILE) -> list[dict]:
    chunks: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def tokenize(text: str) -> list[str]:
    ascii_terms = re.findall(r"[A-Za-z0-9_+-]+", text.lower())
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    terms: list[str] = ascii_terms + chinese_terms

    for term in chinese_terms:
        if len(term) > 2:
            terms.extend(term[index : index + 2] for index in range(len(term) - 1))
    return terms


def infer_query_phrases(question: str) -> list[str]:
    phrases: list[str] = []
    phrase_rules = [
        ("学院", "领导", "学院领导"),
        ("软件学院", "领导", "学院领导"),
        ("软件学院", "简介", "学院简介"),
        ("软件学院", "标识", "学院标识"),
        ("软件学院", "机构", "机构设置"),
        ("软件学院", "联系", "联系我们"),
        ("软件学院", "荣誉", "学院荣誉"),
        ("软件学院", "优秀", "学院荣誉"),
        ("软件学院", "项目", "项目成果"),
        ("软件学院", "成果", "项目成果"),
        ("软件学院", "科研", "科研项目"),
        ("软件学院", "实训", "实训项目"),
        ("软件学院", "教学", "教学成果"),
        ("软件学院", "竞赛", "学院荣誉"),
        ("软件学院", "大赛", "学院荣誉"),
    ]
    for left, right, phrase in phrase_rules:
        if left in question and right in question:
            phrases.append(phrase)

    direct_phrases = [
        "河北师范大学",
        "软件学院",
        "教务处",
        "学院领导",
        "学院简介",
        "学院荣誉",
        "学院标识",
        "机构设置",
        "联系我们",
        "科研项目",
        "项目成果",
        "实训项目",
        "教学成果",
        "学院之星",
        "创新大赛",
        "创新创业",
        "优秀案例",
        "培养方案",
        "转专业",
        "考试安排",
    ]
    phrases.extend(phrase for phrase in direct_phrases if phrase in question)
    return list(dict.fromkeys(phrases))


def chunk_to_result(chunk: dict, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(chunk.get("chunk_id", "")),
        title=str(chunk.get("title", "")),
        category=str(chunk.get("category", "")),
        source_file=str(chunk.get("source_file", "")),
        heading=str(chunk.get("heading", "")),
        text=str(chunk.get("text", "")),
        score=score,
        source_url=chunk.get("source_url", ""),
        site=chunk.get("site", ""),
        published_at=chunk.get("published_at", ""),
    )


def category_matches(chunk: dict, category: str | None) -> bool:
    if category is None:
        return True
    return chunk.get("category") in {category, "web"}


class KeywordRetriever:
    def __init__(self, chunks_file: Path = DEFAULT_CHUNKS_FILE):
        self.chunks = load_chunks(chunks_file)

    def search(
        self,
        question: str,
        *,
        category: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        query_terms = tokenize(question)
        if not query_terms:
            return []

        scored: list[RetrievedChunk] = []
        for chunk in self.chunks:
            if not category_matches(chunk, category):
                continue
            haystack = (
                f"{chunk.get('title', '')} {chunk.get('heading', '')} "
                f"{chunk.get('source_url', '')} {chunk.get('text', '')}"
            ).lower()
            score = self._score(query_terms + infer_query_phrases(question), haystack, chunk)
            score += self._concept_boost(question, chunk)
            if score > 0:
                scored.append(chunk_to_result(chunk, score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _score(query_terms: list[str], haystack: str, chunk: dict) -> float:
        score = 0.0
        unique_terms = set(query_terms)
        for term in unique_terms:
            count = haystack.count(term.lower())
            if count:
                score += 1.0 + math.log(count)

        title = str(chunk.get("title", "")).lower()
        heading = str(chunk.get("heading", "")).lower()
        for term in unique_terms:
            lower = term.lower()
            if lower in title:
                score += 3.0
            if lower in heading:
                score += 1.5
        return score

    @staticmethod
    def _concept_boost(question: str, chunk: dict) -> float:
        title = str(chunk.get("title", ""))
        source_url = str(chunk.get("source_url", ""))
        site = str(chunk.get("site", ""))
        heading = str(chunk.get("heading", ""))
        text = str(chunk.get("text", ""))
        search_text = f"{title} {heading} {source_url} {text[:1200]}"
        score = 0.0

        if "软件学院" in question and site == "software.hebtu.edu.cn":
            score += 8.0
        if "领导" in question:
            if "领导" in title:
                score += 40.0
            if "/xyld/" in source_url:
                score += 35.0
            if "学院之星" in title:
                score -= 15.0
        if "机构" in question and ("机构" in title or "/cydh/" in source_url):
            score += 25.0
        if "联系" in question and ("联系" in title or "/lxwm/" in source_url):
            score += 25.0
        if any(word in question for word in ["项目", "成果", "优秀", "荣誉", "竞赛", "大赛", "实训", "实践"]):
            if site == "software.hebtu.edu.cn":
                score += 10.0
            for path in ["/kyhz/kyxm/", "/kyhz/xmcg/", "/jyjx/jxcg/", "/xygk/xyry/", "/xmsx/"]:
                if path in source_url:
                    score += 35.0
            for word in ["项目", "成果", "荣誉", "竞赛", "大赛", "实训", "实践", "优秀案例", "AI+PBL", "创新"]:
                if word in title:
                    score += 18.0
                elif word in search_text:
                    score += 5.0
            if "学院之星" in title and "项目" in question:
                score -= 10.0
            if "/xyfc/kysx/" in source_url and not any(word in question for word in ["考研", "升学"]):
                score -= 30.0
        return score


class FaissVectorRetriever:
    def __init__(
        self,
        *,
        index_file: Path = DEFAULT_FAISS_INDEX_FILE,
        metadata_file: Path = DEFAULT_FAISS_METADATA_FILE,
        config_file: Path = DEFAULT_FAISS_CONFIG_FILE,
    ):
        self.config_file = config_file
        self.config = json.loads(config_file.read_text(encoding="utf-8"))
        self.index_dir = config_file.parent
        self.index = faiss.read_index(str(index_file))
        self.chunks = load_chunks(metadata_file)
        self.embedding_provider = build_embedding_provider_from_config(
            self.config["embedding"],
            index_dir=self.index_dir,
        )

    def search(
        self,
        question: str,
        *,
        category: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        dense_query = self.embedding_provider.embed_texts([question])

        search_k = min(max(top_k * 5, top_k), len(self.chunks))
        scores, indexes = self.index.search(dense_query, search_k)

        results: list[RetrievedChunk] = []
        for score, index in zip(scores[0], indexes[0], strict=False):
            if index < 0:
                continue
            chunk = self.chunks[int(index)]
            if not category_matches(chunk, category):
                continue
            results.append(chunk_to_result(chunk, float(score)))
            if len(results) >= top_k:
                break
        return results


class HybridRetriever:
    def __init__(self):
        self.keyword_retriever = KeywordRetriever()
        self.vector_retriever = self._load_vector_retriever()

    @staticmethod
    def _load_vector_retriever() -> FaissVectorRetriever | None:
        required_files = [
            DEFAULT_FAISS_INDEX_FILE,
            DEFAULT_FAISS_METADATA_FILE,
            DEFAULT_FAISS_CONFIG_FILE,
        ]
        if not all(path.exists() for path in required_files):
            return None
        return FaissVectorRetriever()

    def search(
        self,
        question: str,
        *,
        category: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        if self.vector_retriever is None:
            return self.keyword_retriever.search(question, category=category, top_k=top_k)

        candidate_k = min(max(top_k * 4, 20), 80)
        vector_results = self.vector_retriever.search(question, category=category, top_k=candidate_k)
        keyword_results = self.keyword_retriever.search(question, category=category, top_k=candidate_k)
        return merge_results(vector_results, keyword_results, top_k=top_k)


def merge_results(
    vector_results: list[RetrievedChunk],
    keyword_results: list[RetrievedChunk],
    *,
    top_k: int,
) -> list[RetrievedChunk]:
    merged: dict[str, RetrievedChunk] = {}
    for rank, result in enumerate(vector_results):
        adjusted_score = safe_score(result) + max(0.0, 1.0 - rank * 0.05)
        merged[result_key(result)] = result_with_score(result, adjusted_score)

    for rank, result in enumerate(keyword_results):
        adjusted_score = safe_score(result) * 0.25 + max(0.0, 0.5 - rank * 0.03)
        key = result_key(result)
        existing = merged.get(key)
        if existing:
            adjusted_score += existing.score
        merged[key] = result_with_score(result, adjusted_score)

    return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:top_k]


def safe_score(result: RetrievedChunk) -> float:
    try:
        return float(getattr(result, "score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def result_key(result: RetrievedChunk) -> str:
    return str(getattr(result, "chunk_id", "")) or str(getattr(result, "source_file", "")) or str(id(result))


def result_with_score(result: RetrievedChunk, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(getattr(result, "chunk_id", "")),
        title=str(getattr(result, "title", "")),
        category=str(getattr(result, "category", "")),
        source_file=str(getattr(result, "source_file", "")),
        heading=str(getattr(result, "heading", "")),
        text=str(getattr(result, "text", "")),
        score=score,
        source_url=str(getattr(result, "source_url", "") or ""),
        site=str(getattr(result, "site", "") or ""),
        published_at=str(getattr(result, "published_at", "") or ""),
    )
