import os
import re
import numpy as np
from typing import List, Optional

class EmbeddingProvider:
    """
    Unified Embedding Provider supporting both Lexical Feature Hashing and
    Transformer-based Semantic Sentence Embeddings.
    Allows A/B evaluation between lexical hashing and genuine semantic vector representations.
    """
    _ST_MODEL = None
    _ST_MODEL_NAME = os.environ.get("SEMANTIC_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    @classmethod
    def _get_semantic_model(cls):
        """Lazy loader for SentenceTransformer model with fallback handling."""
        if cls._ST_MODEL is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._ST_MODEL = SentenceTransformer(cls._ST_MODEL_NAME)
            except Exception as e:
                # Logging fallback if sentence_transformers unavailable or model download restricted
                cls._ST_MODEL = False
        return cls._ST_MODEL if cls._ST_MODEL is not False else None

    @classmethod
    def encode_lexical_hash(cls, text: str, dimension: int = 128) -> List[float]:
        """
        Generates a 128-dimensional L2-normalized bag-of-words feature hashing vector.
        Technically classified as Lexical Feature Hashing (not a learned neural embedding).
        """
        words = re.findall(r'\w+', text.lower())
        vec = np.zeros(dimension, dtype=float)

        if not words:
            return vec.tolist()

        for word in words:
            h = hash(word) % dimension
            vec[h] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()

    @classmethod
    def encode_semantic_transformer(cls, text: str) -> List[float]:
        """
        Encodes input text into a learned 384-dimensional dense semantic sentence embedding
        using sentence-transformers (all-MiniLM-L6-v2 / BGE-family model).
        Falls back to lexical hashing if local transformer execution is unavailable.
        """
        model = cls._get_semantic_model()
        if model is not None:
            try:
                embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return embedding.tolist()
            except Exception:
                pass
        
        # Fallback to lexical feature hashing if model unavailable
        return cls.encode_lexical_hash(text)

    @classmethod
    def encode(cls, text: str, provider_type: Optional[str] = None) -> List[float]:
        """
        Primary encoding entrypoint.
        `provider_type`: 'SEMANTIC_TRANSFORMER' or 'LEXICAL_HASH'.
        Defaults to EMBEDDING_PROVIDER environment variable or 'SEMANTIC_TRANSFORMER'.
        """
        mode = provider_type or os.environ.get("EMBEDDING_PROVIDER", "SEMANTIC_TRANSFORMER")
        if mode.upper() == "SEMANTIC_TRANSFORMER":
            return cls.encode_semantic_transformer(text)
        else:
            return cls.encode_lexical_hash(text)

    @classmethod
    def cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Computes Cosine Similarity between any two arbitrary vector representations.
        """
        if not vec_a or not vec_b:
            return 0.0

        a = np.array(vec_a, dtype=float)
        b = np.array(vec_b, dtype=float)

        # Handle potential dimension mismatch gracefully
        if len(a) != len(b):
            # If dimensions differ (e.g. lexical vs semantic comparison), return 0.0 similarity
            return 0.0

        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))


class LocalEmbeddingModel:
    """
    Legacy wrapper maintaining 100% backward compatibility for existing call sites.
    """
    DIMENSION = 128

    @classmethod
    def encode(cls, text: str) -> List[float]:
        return EmbeddingProvider.encode_lexical_hash(text, dimension=cls.DIMENSION)

    @classmethod
    def cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        return EmbeddingProvider.cosine_similarity(vec_a, vec_b)
