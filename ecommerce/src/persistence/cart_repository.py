from sqlalchemy.orm import Session
from app.domain.cart_model import Cart


class CartRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_customer(self, customer_id: str) -> Cart | None:
        raise NotImplementedError

    def save(self, cart: Cart) -> None:
        raise NotImplementedError
