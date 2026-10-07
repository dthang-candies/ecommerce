import numpy as np
from typing import Dict, List, Tuple, Optional, Any


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Computes cosine similarity between two feature vectors:
    s(a, b) = (a . b) / (||a|| * ||b||)
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    numerator = float(np.dot(a, b))
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


class VectorIndex:
    """
    Data Layer: Vector Index
    Stores product embeddings and performs vector similarity search (k-NN / Top-K).
    """

    def __init__(self, embeddings: Optional[Dict[int, Any]] = None):
        self.index: Dict[int, np.ndarray] = {}
        if embeddings:
            for pid, emb in embeddings.items():
                self.index[pid] = np.asarray(emb, dtype=float)

    def add_vector(self, product_id: int, embedding: Any) -> None:
        """Add or update an embedding for a product."""
        self.index[product_id] = np.asarray(embedding, dtype=float)

    def get_vector(self, product_id: int) -> Optional[np.ndarray]:
        """Retrieve embedding for a product."""
        return self.index.get(product_id)

    def load_from_repository(self, repository) -> None:
        """Loads embeddings directly from product repository products."""
        for p in repository.all_products():
            if "id" in p and "embedding" in p:
                self.add_vector(p["id"], p["embedding"])

    def search(self, query_embedding: Any, top_k: Optional[int] = None) -> List[Tuple[int, float]]:
        """
        Retrieves products ranked by cosine similarity with query_embedding.
        Returns a sorted list of (product_id, score) descending.
        """
        q_vec = np.asarray(query_embedding, dtype=float)
        scores: List[Tuple[int, float]] = []

        for product_id, embedding in self.index.items():
            sim = cosine_similarity(q_vec, embedding)
            scores.append((product_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)

        if top_k is not None:
            return scores[:top_k]
        return scores
