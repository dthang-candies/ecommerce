from sqlalchemy.orm import Session


class PromotionRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_code(self, code: str):
        raise NotImplementedError
