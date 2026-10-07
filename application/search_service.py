from typing import List, Tuple, Dict, Any, Optional
import numpy as np


class SearchService:
    """
    Application / Intelligence Layer: Search Service
    Retrieves candidate products or orders across multiple modalities:
    - Keyword/text search
    - Vector image search
    - Multimodal search fusion
    - Order lookup search
    """

    def __init__(
        self,
        repository,
        vector_index=None,
        order_repository=None,
        ranking_service=None
    ):
        self.repository = repository
        self.vector_index = vector_index
        self.order_repository = order_repository
        self.ranking_service = ranking_service

    def search_text(self, query: str) -> List[Tuple[Dict[str, Any], float]]:
        """
        Text/Keyword search:
        Retrieves matching products by counting keyword occurrences
        in product name, category, and color.
        """
        query = query.lower()
        results = []
        words = query.split()

        for product in self.repository.all_products():
            text = (
                product.get("name", "") + " " +
                product.get("category", "") + " " +
                product.get("color", "")
            ).lower()

            score = 0
            for word in words:
                if word in text:
                    score += 1

            if score > 0:
                results.append((product, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def search_image(self, query_embedding: Any, top_k: Optional[int] = None) -> List[Tuple[Dict[str, Any], float]]:
        """
        Image search:
        Retrieves products by cosine similarity against vector embeddings.
        """
        q_vec = np.asarray(query_embedding, dtype=float)
        results = []

        if self.vector_index is not None:
            raw_scores = self.vector_index.search(q_vec, top_k=top_k)
            for pid, score in raw_scores:
                product = self.repository.find_by_id(pid)
                if product:
                    results.append((product, round(float(score), 4)))
        else:
            # Direct calculation if vector index is not separate
            for product in self.repository.all_products():
                if "embedding" in product:
                    p_vec = np.asarray(product["embedding"], dtype=float)
                    num = float(np.dot(q_vec, p_vec))
                    denom = float(np.linalg.norm(q_vec) * np.linalg.norm(p_vec))
                    sim = (num / denom) if denom != 0.0 else 0.0
                    results.append((product, round(sim, 4)))
            results.sort(key=lambda x: x[1], reverse=True)
            if top_k is not None:
                results = results[:top_k]

        return results

    def search_multimodal(
        self,
        query_text: Optional[str] = None,
        query_embedding: Optional[Any] = None,
        lambda_t: float = 0.5,
        lambda_i: float = 0.5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Multimodal search (Section 17 Extension):
        S(p|q) = lambda_t * S_text(p|q_t) + lambda_i * S_image(p|q_i)
        """
        text_scores: Dict[int, float] = {}
        if query_text:
            text_matches = self.search_text(query_text)
            # Normalize text scores into [0, 1] relative to max score
            max_t = max([s for _, s in text_matches], default=1.0)
            if max_t > 0:
                for prod, sc in text_matches:
                    text_scores[prod["id"]] = sc / max_t

        image_scores: Dict[int, float] = {}
        if query_embedding is not None:
            img_matches = self.search_image(query_embedding)
            for prod, sc in img_matches:
                image_scores[prod["id"]] = sc

        combined_results = []
        for product in self.repository.all_products():
            pid = product["id"]
            st = text_scores.get(pid, 0.0)
            si = image_scores.get(pid, 0.0)

            # Combined score formula
            score = (lambda_t * st) + (lambda_i * si)
            if score > 0:
                combined_results.append((product, round(score, 4)))

        combined_results.sort(key=lambda x: x[1], reverse=True)
        return combined_results

    def search_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Order search (Section 18 Extension):
        Retrieves order details by order_id.
        """
        if self.order_repository is not None:
            return self.order_repository.find_order(order_id)
        return None
