from app.persistence.product_repository import ProductRepository


class ProductService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def search(self, keyword: str | None = None):
        raise NotImplementedError

    def get_detail(self, product_id: str):
        raise NotImplementedError
