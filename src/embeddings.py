"""Embedding providers used by FAISS index building and querying."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import normalize


DEFAULT_HASHING_FEATURES = 4096
DEFAULT_SENTENCE_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_API_MODEL = "text-embedding-3-small"


class EmbeddingProvider(Protocol):
    dimension: int | None

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalized float32 vectors."""

    def to_config(self) -> dict[str, Any]:
        """Return serializable provider configuration."""


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)


class HashingEmbeddingProvider:
    def __init__(self, *, n_features: int = DEFAULT_HASHING_FEATURES, vectorizer: HashingVectorizer | None = None):
        self.n_features = n_features
        self.vectorizer = vectorizer or HashingVectorizer(
            n_features=n_features,
            alternate_sign=False,
            norm=None,
            analyzer="char_wb",
            ngram_range=(2, 4),
            lowercase=True,
        )
        self.dimension = n_features

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        matrix = self.vectorizer.transform(texts)
        matrix = normalize(matrix, norm="l2", copy=False)
        return matrix.astype(np.float32).toarray()

    def save(self, path: Path) -> None:
        with path.open("wb") as file:
            pickle.dump(self.vectorizer, file)

    @classmethod
    def load(cls, path: Path, *, n_features: int = DEFAULT_HASHING_FEATURES) -> "HashingEmbeddingProvider":
        with path.open("rb") as file:
            vectorizer = pickle.load(file)
        return cls(n_features=n_features, vectorizer=vectorizer)

    def to_config(self) -> dict[str, Any]:
        return {
            "backend": "hashing",
            "n_features": self.n_features,
            "dimension": self.dimension,
            "normalized": True,
        }


class SentenceTransformersEmbeddingProvider:
    def __init__(self, *, model_name: str = DEFAULT_SENTENCE_MODEL, local_files_only: bool = False):
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        from transformers.utils import logging as transformers_logging
        from sentence_transformers import SentenceTransformer

        transformers_logging.set_verbosity_error()
        self.model_name = model_name
        self.local_files_only = local_files_only
        self.model = SentenceTransformer(model_name, local_files_only=local_files_only)
        self.dimension = int(self.model.get_sentence_embedding_dimension())

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(
            texts,
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.astype(np.float32)

    def to_config(self) -> dict[str, Any]:
        return {
            "backend": "sentence-transformers",
            "model": self.model_name,
            "dimension": self.dimension,
            "normalized": True,
            "local_files_only": self.local_files_only,
        }


class ApiEmbeddingProvider:
    def __init__(
        self,
        *,
        model: str = DEFAULT_API_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        load_dotenv()
        self.model = model
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        if not self.api_key:
            raise RuntimeError("Missing EMBEDDING_API_KEY or OPENAI_API_KEY in .env")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.dimension: int | None = None

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        response = self.client.embeddings.create(model=self.model, input=texts)
        vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
        self.dimension = int(vectors.shape[1])
        return l2_normalize(vectors)

    def to_config(self) -> dict[str, Any]:
        return {
            "backend": "api",
            "model": self.model,
            "base_url": self.base_url,
            "dimension": self.dimension,
            "normalized": True,
        }


def build_embedding_provider(
    backend: str,
    *,
    model: str | None = None,
    n_features: int = DEFAULT_HASHING_FEATURES,
    vectorizer_file: Path | None = None,
    local_files_only: bool = False,
) -> EmbeddingProvider:
    if backend == "hashing":
        if vectorizer_file and vectorizer_file.exists():
            return HashingEmbeddingProvider.load(vectorizer_file, n_features=n_features)
        return HashingEmbeddingProvider(n_features=n_features)
    if backend == "sentence-transformers":
        return SentenceTransformersEmbeddingProvider(
            model_name=model or DEFAULT_SENTENCE_MODEL,
            local_files_only=local_files_only,
        )
    if backend == "api":
        return ApiEmbeddingProvider(model=model or os.getenv("EMBEDDING_MODEL") or DEFAULT_API_MODEL)
    raise ValueError(f"Unsupported embedding backend: {backend}")


def build_embedding_provider_from_config(config: dict[str, Any], *, index_dir: Path) -> EmbeddingProvider:
    backend = config["backend"]
    if backend == "hashing":
        vectorizer_path = index_dir / config.get("vectorizer_file", "vectorizer.pkl")
        return build_embedding_provider(
            backend,
            n_features=int(config.get("n_features", DEFAULT_HASHING_FEATURES)),
            vectorizer_file=vectorizer_path,
        )
    return build_embedding_provider(backend, model=config.get("model"), local_files_only=True)
