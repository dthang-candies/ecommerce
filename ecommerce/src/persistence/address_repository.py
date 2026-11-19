from sqlalchemy.orm import Session
from app.domain.customer_model import Address


class AddressRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_for_customer(self, customer_id: str) -> list[Address]:
        raise NotImplementedError
