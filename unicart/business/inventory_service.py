from __future__ import annotations

import logging

from ..domain.enums import MovementType
from ..domain.models import Inventory
from ..persistence.repositories import InventoryRepository
from .exceptions import BusinessError, NotFound
from .transaction import transactional

audit = logging.getLogger("unicart.audit")


class InventoryService:
    """UC-12 Manage Inventory (BR-11: alert when quantity <= threshold)."""

    def __init__(self, session, inventory: InventoryRepository):
        self.session, self.inventory = session, inventory

    def low_stock_report(self) -> list[Inventory]:
        return self.inventory.low_stock()

    def list(self, keyword, page, size):
        return self.inventory.list_all(keyword, max(page, 1), min(size, 100))

    def summary(self) -> dict:
        return self.inventory.summary()

    def movements(self, product_id: int):
        if self.inventory.get(product_id) is None:
            raise NotFound("Sản phẩm không tồn tại")
        return self.inventory.movements(product_id)

    @transactional
    def restock(self, product_id: int, qty: int, staff_id: int) -> Inventory:
        """Goods physically received: increase stock and log it (also used by RestockService.receive)."""
        if qty <= 0:
            raise BusinessError("Số lượng phải lớn hơn 0")
        if self.inventory.get(product_id) is None:
            raise NotFound("Sản phẩm không tồn tại")
        self.inventory.increase(product_id, qty)
        self.inventory.log(product_id, MovementType.IN.value, qty, f"RESTOCK by {staff_id}", None)
        self.session.flush()
        inv = self.inventory.get(product_id)
        self.session.refresh(inv)
        return inv

    @transactional
    def set_threshold(self, product_id: int, min_threshold: int, staff_id: int) -> Inventory:
        inv = self.inventory.get(product_id)
        if inv is None:
            raise NotFound("Sản phẩm không tồn tại")
        if min_threshold < 0:
            raise BusinessError("Ngưỡng tối thiểu không được âm")
        inv.min_threshold = min_threshold
        audit.info("staff=%s set min_threshold of product=%s to %s", staff_id, product_id, min_threshold)
        return inv
