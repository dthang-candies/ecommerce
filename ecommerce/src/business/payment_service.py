from app.persistence.order_repository import OrderRepository
from app.persistence.payment_repository import PaymentRepository


class PaymentService:
    def __init__(self, payment_repo: PaymentRepository, order_repo: OrderRepository):
        self.payment_repo = payment_repo
        self.order_repo = order_repo

    def handle_callback(self, payload: dict):
        raise NotImplementedError
