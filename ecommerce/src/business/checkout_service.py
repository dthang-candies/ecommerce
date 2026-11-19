from app.business.pricing_calculator import PricingCalculator
from app.persistence.address_repository import AddressRepository
from app.persistence.cart_repository import CartRepository
from app.persistence.inventory_repository import InventoryRepository
from app.persistence.order_repository import OrderRepository
from app.persistence.promotion_repository import PromotionRepository


class CheckoutService:
    def __init__(self, cart_repo: CartRepository, order_repo: OrderRepository,
                 inventory_repo: InventoryRepository, address_repo: AddressRepository,
                 promotion_repo: PromotionRepository, pricing: PricingCalculator):
        self.cart_repo = cart_repo
        self.order_repo = order_repo
        self.inventory_repo = inventory_repo
        self.address_repo = address_repo
        self.promotion_repo = promotion_repo
        self.pricing = pricing

    def place_order(self, customer_id: str, address_id: str, payment_method: str,
                    promo_code: str | None = None):
        raise NotImplementedError
