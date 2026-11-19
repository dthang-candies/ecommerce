"""ProductModel: Category, Product (+Book/Electronic/Laptop/Mobile/Shoes/Clothes), StockMovement."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Category:
    category_id: str
    name: str


@dataclass
class Product:
    product_id: str
    name: str
    description: str
    price: float
    stock_quantity: int

    def is_visible(self) -> bool:
        raise NotImplementedError

    def in_stock(self, quantity: int) -> bool:
        raise NotImplementedError


@dataclass
class Book(Product):
    isbn: str = ""
    title: str = ""
    author: str = ""
    publisher: str = ""


@dataclass
class Electronic(Product):
    brand: str = ""
    model: str = ""
    warranty_months: int = 0


@dataclass
class Laptop(Electronic):
    cpu: str = ""
    ram: str = ""
    storage: str = ""


@dataclass
class Mobile(Electronic):
    screen_size: float = 0.0
    storage: str = ""
    battery_capacity: int = 0


@dataclass
class Shoes(Product):
    shoes_size: int = 0
    shoes_type: str = ""


@dataclass
class Clothes(Product):  # "Closes" trong sơ đồ
    size: str = ""
    color: str = ""
    material: str = ""


@dataclass
class StockMovement:
    movement_id: str
    product_id: str
    delta: int
    reason: str
    created_at: datetime
