"""
Embedding Service — OpenAI text-embedding-3-small
Generates dense vectors for chunks.
"""
import os
import time
import hashlib
import math
from typing import Optional

from openai import OpenAI

from core.config import EMBEDDING_MODEL, EMBEDDING_DIM


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


def _offline_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """
    Deterministic local fallback embedding.

    This keeps the pipeline operational in environments without OpenAI access.
    The vector is derived from token hashes, so equal text yields equal vectors.
    """
    vector = [0.0] * dim
    tokens = [tok for tok in text.lower().split() if tok]
    if not tokens:
        return vector

    for token in tokens[:2048]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        weight = 1.0 + (digest[4] / 255.0)
        vector[idx] += weight

    norm = math.sqrt(sum(v * v for v in vector))
    if norm <= 0:
        return vector
    return [v / norm for v in vector]


def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    """
    Generate embedding for a single text.
    Truncates to 8000 tokens (safe for embedding models).

    Returns:
        List of 1536 floats (embedding vector)
    """
    if not client.api_key:
        return _offline_embedding(text)

    # Truncate if too long (embedding models have context limits)
    truncated = text[:8000]

    response = client.embeddings.create(
        model=model,
        input=truncated
    )

    return response.data[0].embedding


def get_embeddings_batch(texts: list[str], model: str = EMBEDDING_MODEL) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in batch.
    Qdrant client handles batching internally but we wrap here for convenience.

    Returns:
        List of embedding vectors (1536 dims each)
    """
    if not client.api_key:
        return [_offline_embedding(text) for text in texts]

    if not texts:
        return []

    # Truncate each text
    truncated = [t[:8000] for t in texts]

    response = client.embeddings.create(
        model=model,
        input=truncated
    )

    return [item.embedding for item in response.data]


def estimate_cost(texts: list[str], model: str = EMBEDDING_MODEL) -> float:
    """
    Estimate embedding cost in USD.
    text-embedding-3-small: $0.02 per 1M tokens (Mar 2024)
    Approximate: 1 token ≈ 4 chars
    """
    total_chars = sum(len(t) for t in texts)
    total_tokens = total_chars / 4
    price_per_million = 0.02
    return (total_tokens / 1_000_000) * price_per_million
