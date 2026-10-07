from typing import List, Tuple, Dict, Any, Optional


class RankingService:
    """
    Application / Intelligence Layer: Ranking Service
    Ranks candidate retrieval results using multi-signal scoring:
    S(x|q) = alpha * S_text + beta * S_image + gamma * S_business
    """

    def __init__(self, alpha: float = 0.6, beta: float = 0.3, gamma: float = 0.1):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def calculate_business_score(self, product: Dict[str, Any]) -> float:
        """
        Calculates business signal based on stock availability and price competitiveness:
        - In-stock products receive higher priority (stock > 0).
        - Normalized to [0.0, 1.0].
        """
        stock = product.get("stock", 0)
        stock_factor = 1.0 if stock > 0 else 0.0

        # Gentle bonus for in-stock and reasonable pricing
        price = product.get("price", 100)
        price_factor = 1.0 / (1.0 + (price / 200.0))  # Smooth decay

        return (stock_factor * 0.7) + (price_factor * 0.3)

    def rank(
        self,
        candidates: List[Tuple[Dict[str, Any], float]],
        business_weight: Optional[float] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Ranks candidate results by adjusting retrieval score with business signals.
        Returns sorted list of (product, final_score) in descending order.
        """
        if not candidates:
            return []

        gamma = self.gamma if business_weight is None else business_weight
        base_weight = 1.0 - gamma

        max_raw_score = max([score for _, score in candidates], default=1.0)
        if max_raw_score <= 0:
            max_raw_score = 1.0

        ranked: List[Tuple[Dict[str, Any], float]] = []
        for product, raw_score in candidates:
            normalized_raw = raw_score / max_raw_score
            business_score = self.calculate_business_score(product)

            # Combined multi-signal score
            final_score = (base_weight * normalized_raw) + (gamma * business_score)
            ranked.append((product, round(final_score, 4)))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
