from app.business.actor import Actor
from app.business.order_status_policy import OrderStatusPolicy
from app.persistence.inventory_repository import InventoryRepository
from app.persistence.order_repository import OrderRepository


class OrderService:
    def __init__(self, order_repo: OrderRepository, inventory_repo: InventoryRepository,
                 policy: OrderStatusPolicy):
        self.order_repo = order_repo
        self.inventory_repo = inventory_repo
        self.policy = policy

    def change_status(self, actor: Actor, order_id: str, new_status: str):
        raise NotImplementedError

    def cancel(self, actor: Actor, order_id: str):
        raise NotImplementedError

    def list_for_customer(self, customer_id: str):
        raise NotImplementedError

    def expire_unpaid(self):
        raise NotImplementedError
