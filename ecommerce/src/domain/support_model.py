"""SupportModel: Review, Supplier."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Review:
    review_id: str
    product_id: str
    customer_id: str
    rating: int
    comment: str


@dataclass
class Supplier:
    supplier_id: str
    name: str
    contact: str
