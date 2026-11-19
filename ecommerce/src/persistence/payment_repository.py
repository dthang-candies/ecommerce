from sqlalchemy.orm import Session
from app.domain.order_model import Payment


class PaymentRepository:
    def __init__(self, session: Session):
        self.session = session

    def by_order(self, order_id: str) -> Payment | None:
        raise NotImplementedError

    def by_transaction(self, transaction_id: str) -> Payment | None:
        raise NotImplementedError
