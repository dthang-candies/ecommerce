import numpy as np
from typing import Any, Dict, List, Tuple, Optional


class ImageService:
    """
    Application / Intelligence Layer: Image Service
    Responsible for extracting image feature representations f_theta(I)
    and calculating visual cosine similarity between query and product images.
    """

    def __init__(self):
        # Sample predefined visual prototypes for simulated image uploads
        self.preset_prototypes: Dict[str, np.ndarray] = {
            "shoes": np.array([0.9, 0.1, 0.2], dtype=float),
            "running_shoes": np.array([0.9, 0.15, 0.15], dtype=float),
            "bag": np.array([0.1, 0.2, 0.9], dtype=float),
            "leather_bag": np.array([0.15, 0.25, 0.85], dtype=float),
            "clothing": np.array([0.3, 0.7, 0.4], dtype=float),
            "watch": np.array([0.4, 0.5, 0.6], dtype=float)
        }

    def encode_image(self, image_input: Any) -> np.ndarray:
        """
        Simulated feature encoder f_theta(I):
        Converts an image file/path, key, or raw vector into feature embedding z_q.
        """
        if isinstance(image_input, (list, tuple, np.ndarray)):
            return np.asarray(image_input, dtype=float)
        elif isinstance(image_input, str):
            clean_key = image_input.lower().strip()
            for key, vec in self.preset_prototypes.items():
                if key in clean_key:
                    return vec.copy()
            # Default fallback embedding if unrecognized string
            return np.array([0.5, 0.5, 0.5], dtype=float)
        # Fallback default
        return np.array([0.5, 0.5, 0.5], dtype=float)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Cosine similarity: s(I_q, I_p) = (z_q^T z_p) / (||z_q|| * ||z_p||)
        """
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
