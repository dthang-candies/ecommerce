from sqlalchemy.orm import Session


class InventoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def try_decrease(self, product_id: str, quantity: int) -> bool:
        raise NotImplementedError

    def increase(self, product_id: str, quantity: int) -> None:
        raise NotImplementedError

    def log(self, product_id: str, delta: int, reason: str) -> None:
        raise NotImplementedError

    def low_stock(self, threshold: int) -> list:
        raise NotImplementedError
