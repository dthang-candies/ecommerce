from app.business.actor import Actor


class OrderStatusPolicy:
    def can_transaction(self, actor: Actor, current: str, new: str) -> bool:
        raise NotImplementedError
