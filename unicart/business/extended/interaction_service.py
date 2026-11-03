from ...domain.enums import EventType
from ...domain.models import InteractionLog
from ...persistence.repositories import InteractionRepository, ProductRepository
from ..exceptions import BusinessError
from ..transaction import transactional

# PURCHASE is written by CheckoutService only; clients may report just these events (UC-16, FR-19).
CLIENT_EVENTS = {EventType.VIEW, EventType.SEARCH, EventType.CLICK_REC, EventType.REC_IMPRESSION}


class InteractionService:
    """UC-16 Track User Interactions. Stores only what the models need (data minimisation, 3.5.2)."""

    def __init__(self, session, interactions: InteractionRepository, products: ProductRepository):
        self.session, self.interactions, self.products = session, interactions, products

    @transactional
    def log(self, customer_id: int | None, event: EventType, product_id: int | None = None,
            keyword: str | None = None) -> None:
        if event not in CLIENT_EVENTS:
            raise BusinessError("Loại sự kiện không hợp lệ")
        if product_id is not None and self.products.get(product_id) is None:
            return                                                 # unknown product: drop silently, never fail the page
        keyword = (keyword or "").strip()[:150] or None
        self.interactions.add(InteractionLog(customer_id=customer_id, product_id=product_id,
                                             event_type=event.value, keyword=keyword))
