from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.order_model import CustomerOrder


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, order: CustomerOrder) -> CustomerOrder:
        raise NotImplementedError

    def get(self, order_id: str) -> CustomerOrder | None:
        raise NotImplementedError

    def list_by_customer(self, customer_id: str) -> list[CustomerOrder]:
        raise NotImplementedError

    def unpaid_before(self, deadline: datetime) -> list[CustomerOrder]:
        raise NotImplementedError
