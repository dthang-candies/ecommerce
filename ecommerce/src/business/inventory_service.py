from app.persistence.inventory_repository import InventoryRepository


class InventoryService:
    def __init__(self, inventory_repo: InventoryRepository):
        self.inventory_repo = inventory_repo

    def low_stock_report(self, threshold: int = 5):
        raise NotImplementedError

    def restock(self, product_id: str, quantity: int):
        raise NotImplementedError
