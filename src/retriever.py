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

    # Credit / score queries: boost program-category chunks
    credit_keywords = ["学分", "学时", "几分", "多少分", "绩点", "周学时", "考核",
                       "必修", "选修", "先修", "课程类别", "课程性质"]
    if any(kw in question for kw in credit_keywords):
        phrases.append("学分")
        phrases.append("学时")
        phrases.append("课程代码")
        phrases.append("必修")

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
    chunk_cat = chunk.get("category", "")
    if chunk_cat in {category, "web"}:
        return True
    # Course queries also need program data (培养方案 has course credits)
    if category == "courses" and chunk_cat == "programs":
        return True
    return False


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

        # ── Noise penalties: suppress known low-quality / irrelevant chunks ──
        score += KeywordRetriever._noise_penalty(question, chunk)

        if "软件学院" in question and site == "software.hebtu.edu.cn":
            score += 8.0

        # ── School-info queries: boost specific pages ──
        if any(kw in question for kw in ["校区", "在哪", "地址", "位置"]):
            if "软件学院" in title or "网络教育学院" in title:
                score += 40.0
        if "院长" in question or "领导" in question:
            if "领导" in title or "领导" in source_url:
                score += 50.0
            if "学院简介" in title:
                score += 25.0
        if any(kw in question for kw in ["教师", "老师", "师资", "教授", "教职工"]):
            if "领导" in title or "领导" in source_url:
                score += 60.0
            if "学院简介" in title or "师资" in title:
                score += 25.0
            # Boost any page that contains person names/titles
            if any(t in text for t in ["书记", "院长", "教授", "讲师"]):
                score += 15.0
        chunk_cat = str(chunk.get("category", ""))
        if any(kw in question for kw in ["选课", "退课", "办理", "申请", "流程"]):
            if chunk_cat == "policies":
                score += 25.0
            if "选课" in title or "选课" in text:
                score += 30.0
            if "休学" in title or "休学" in text:
                score += 35.0
            if "缓考" in title or "缓考" in text:
                score += 30.0

        # Credit / course-info queries: boost program chunks heavily
        credit_keywords = ["学分", "学时", "几分", "多少分", "绩点", "周学时", "考核方式",
                           "必修", "选修", "先修", "课程类别", "课程性质"]
        if any(kw in question for kw in credit_keywords):
            cat = str(chunk.get("category", ""))
            if cat == "programs":
                score += 30.0
            elif cat == "courses":
                score += 10.0
            # Boost syllabus metadata sections that contain credit/requirement info
            heading = str(chunk.get("heading", ""))
            metadata_headings = ["课程说明", "一、课程说明", "课程信息", "基本信息"]
            if any(h in heading for h in metadata_headings):
                score += 15.0
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

    @staticmethod
    def _noise_penalty(question: str, chunk: dict) -> float:
        """Penalize known noise documents and low-quality web pages."""
        title = str(chunk.get("title", ""))
        text = str(chunk.get("text", ""))
        source_url = str(chunk.get("source_url", ""))
        site = str(chunk.get("site", ""))
        cat = str(chunk.get("category", ""))

        penalty = 0.0

        # ── Known noise news articles (not academic) ──
        noise_titles = [
            "典耀中华", "阅读大会", "毽球比赛", "音乐会",
        ]
        for nt in noise_titles:
            if nt in title:
                penalty -= 50.0
                break

        # ── Short web pages are usually just navigation / index pages ──
        if cat == "web" and len(text) < 300:
            penalty -= 30.0

        # ── News site chunks are rarely relevant for academic queries ──
        academic_query = any(kw in question for kw in [
            "学分", "课程", "考试", "毕业", "补考", "重修", "必修", "选修",
            "培养方案", "考核", "成绩", "绩点", "学位", "学籍",
        ])
        if academic_query and site == "news.hebtu.edu.cn":
            penalty -= 20.0

        # ── Generic index/navigation pages ──
        nav_titles = {"师大要闻", "综合新闻", "基层动态", "学术动态", "通知公告",
                       "教学动态", "学工动态", "学院新闻", "重要通知",
                       "党旗飘扬", "立德树人", "学习参考", "文件精神",
                       "媒体师大", "校园风光", "校园地图"}
        if title in nav_titles:
            penalty -= 35.0

        # ── Short, low-content pages that are just link lists ──
        if cat == "web" and len(text) < 150:
            penalty -= 45.0

        return penalty


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
    """Merge vector and keyword results using Reciprocal Rank Fusion (RRF).

    Keyword results are weighted 1.5x higher than vector results.  With
    BGE-small-zh providing good Chinese semantic vectors, the weights are
    more balanced than with the old HashingVectorizer.
    """
    merged: dict[str, RetrievedChunk] = {}
    k = 60  # RRF damping constant
    kw_weight = 1.5
    vec_weight = 1.0

    for rank, result in enumerate(vector_results):
        rrf = vec_weight / (k + rank)
        merged[result_key(result)] = result_with_score(result, rrf)

    for rank, result in enumerate(keyword_results):
        rrf = kw_weight / (k + rank)
        key = result_key(result)
        existing = merged.get(key)
        merged[key] = result_with_score(
            result,
            existing.score + rrf if existing else rrf,
        )

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
