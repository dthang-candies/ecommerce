from sqlalchemy.orm import Session
from app.domain.product_model import Product


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, product_id: str) -> Product | None:
        raise NotImplementedError

    def search(self, keyword: str | None = None) -> list[Product]:
        raise NotImplementedError
