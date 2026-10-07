from typing import Dict, Any, Optional


class QueryService:
    """
    Application / Intelligence Layer: Query Service
    Converts different input modalities into a unified common query representation.
    Design Principle: {text, voice, image, multimodal} -> Common Query Object.
    """

    def text_query(self, text: str) -> Dict[str, Any]:
        """Convert a keyword or text query into standard query representation."""
        return {
            "type": "text",
            "query": text.strip() if text else ""
        }

    def voice_query(self, text: str) -> Dict[str, Any]:
        """Convert a transcribed voice query into standard query representation."""
        return {
            "type": "voice",
            "query": text.strip() if text else ""
        }

    def image_query(self, embedding: Any) -> Dict[str, Any]:
        """Convert an image feature embedding into standard query representation."""
        return {
            "type": "image",
            "embedding": embedding
        }

    def multimodal_query(
        self,
        text: Optional[str] = None,
        embedding: Optional[Any] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Multimodal query extension:
        Combines text and image representations with weight parameters lambda_t and lambda_i.
        """
        if weights is None:
            weights = {"text": 0.5, "image": 0.5}

        return {
            "type": "multimodal",
            "query": text.strip() if text else "",
            "embedding": embedding,
            "weights": weights
        }

    def order_query(self, order_id: str) -> Dict[str, Any]:
        """Convert an order search request into query representation."""
        return {
            "type": "order",
            "order_id": order_id.strip() if order_id else ""
        }
