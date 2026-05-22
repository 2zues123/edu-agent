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
            if category and chunk["category"] != category:
                continue
            haystack = f"{chunk['title']} {chunk['heading']} {chunk['text']}".lower()
            score = self._score(query_terms, haystack, chunk)
            if score > 0:
                scored.append(
                    RetrievedChunk(
                        chunk_id=chunk["chunk_id"],
                        title=chunk["title"],
                        category=chunk["category"],
                        source_file=chunk["source_file"],
                        heading=chunk["heading"],
                        text=chunk["text"],
                        score=score,
                    )
                )

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

        title = chunk["title"].lower()
        heading = chunk["heading"].lower()
        for term in unique_terms:
            lower = term.lower()
            if lower in title:
                score += 3.0
            if lower in heading:
                score += 1.5
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
            if category and chunk["category"] != category:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk["chunk_id"],
                    title=chunk["title"],
                    category=chunk["category"],
                    source_file=chunk["source_file"],
                    heading=chunk["heading"],
                    text=chunk["text"],
                    score=float(score),
                )
            )
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

        vector_results = self.vector_retriever.search(question, category=category, top_k=top_k)
        keyword_results = self.keyword_retriever.search(question, category=category, top_k=top_k)
        return merge_results(vector_results, keyword_results, top_k=top_k)


def merge_results(
    vector_results: list[RetrievedChunk],
    keyword_results: list[RetrievedChunk],
    *,
    top_k: int,
) -> list[RetrievedChunk]:
    merged: dict[str, RetrievedChunk] = {}
    for rank, result in enumerate(vector_results):
        adjusted_score = result.score + max(0.0, 1.0 - rank * 0.05)
        merged[result.chunk_id] = RetrievedChunk(**{**result.__dict__, "score": adjusted_score})

    for rank, result in enumerate(keyword_results):
        adjusted_score = result.score * 0.25 + max(0.0, 0.5 - rank * 0.03)
        existing = merged.get(result.chunk_id)
        if existing:
            adjusted_score += existing.score
        merged[result.chunk_id] = RetrievedChunk(**{**result.__dict__, "score": adjusted_score})

    return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:top_k]
