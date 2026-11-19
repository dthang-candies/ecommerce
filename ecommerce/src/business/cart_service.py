from app.persistence.cart_repository import CartRepository
from app.persistence.product_repository import ProductRepository


class CartService:
    def __init__(self, cart_repo: CartRepository, product_repo: ProductRepository):
        self.cart_repo = cart_repo
        self.product_repo = product_repo

    def view(self, customer_id: str):
        raise NotImplementedError

    def add_item(self, customer_id: str, product_id: str, quantity: int):
        raise NotImplementedError

    def update_quantity(self, customer_id: str, product_id: str, quantity: int):
        raise NotImplementedError

    def remove_item(self, customer_id: str, product_id: str):
        raise NotImplementedError
