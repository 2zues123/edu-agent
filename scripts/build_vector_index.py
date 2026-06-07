#!/usr/bin/env python3
"""Build a local FAISS vector index from generated JSONL chunks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import faiss

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.embeddings import DEFAULT_HASHING_FEATURES, DEFAULT_SENTENCE_MODEL, HashingEmbeddingProvider, build_embedding_provider


CHUNKS_FILE = Path("data/processed/chunks.jsonl")
INDEX_DIR = Path("data/index/faiss")
INDEX_FILE = INDEX_DIR / "chunks.faiss"
METADATA_FILE = INDEX_DIR / "metadata.jsonl"
VECTORIZER_FILE = INDEX_DIR / "vectorizer.pkl"
CONFIG_FILE = INDEX_DIR / "index_config.json"


def load_chunks(path: Path) -> list[dict]:
    chunks: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def chunk_to_text(chunk: dict) -> str:
    return "\n".join(
        [
            chunk.get("title", ""),
            chunk.get("category", ""),
            chunk.get("heading", ""),
            chunk.get("text", ""),
        ]
    )


def write_metadata(chunks: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def build_index(args: argparse.Namespace) -> int:
    chunks = load_chunks(args.chunks)
    if not chunks:
        raise RuntimeError(f"No chunks found in {args.chunks}")

    texts = [chunk_to_text(chunk) for chunk in chunks]
    provider = build_embedding_provider(
        args.embedding_backend,
        model=args.embedding_model,
        n_features=args.n_features,
    )
    vectors = provider.embed_texts(texts)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    args.index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(args.index_file))
    write_metadata(chunks, args.metadata_file)

    provider_config = provider.to_config()
    if isinstance(provider, HashingEmbeddingProvider):
        provider.save(args.vectorizer_file)
        provider_config["vectorizer_file"] = args.vectorizer_file.name

    config = {
        "chunks_file": str(args.chunks),
        "index_file": args.index_file.name,
        "metadata_file": args.metadata_file.name,
        "embedding": provider_config,
    }
    args.config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Chunks: {len(chunks)}")
    print(f"Dimensions: {vectors.shape[1]}")
    print(f"Embedding backend: {provider_config['backend']}")
    if provider_config.get("model"):
        print(f"Embedding model: {provider_config['model']}")
    print(f"Index: {args.index_file}")
    print(f"Metadata: {args.metadata_file}")
    print(f"Config: {args.config_file}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, default=CHUNKS_FILE)
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    parser.add_argument("--index-file", type=Path, default=INDEX_FILE)
    parser.add_argument("--metadata-file", type=Path, default=METADATA_FILE)
    parser.add_argument("--vectorizer-file", type=Path, default=VECTORIZER_FILE)
    parser.add_argument("--config-file", type=Path, default=CONFIG_FILE)
    parser.add_argument(
        "--embedding-backend",
        choices=["hashing", "sentence-transformers", "api"],
        default=os.getenv("EMBEDDING_BACKEND", "sentence-transformers"),
    )
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", DEFAULT_SENTENCE_MODEL))
    parser.add_argument("--n-features", type=int, default=DEFAULT_HASHING_FEATURES)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(build_index(parse_args()))
