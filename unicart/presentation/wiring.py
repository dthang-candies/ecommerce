"""Builds the services of one request from one database session (manual dependency injection)."""
from dataclasses import dataclass

from ..business.account_service import AccountService
from ..business.auth_service import AuthService
from ..business.cart_service import CartService
from ..business.catalog_service import CatalogService
from ..business.chat_service import ChatService
from ..business.checkout_service import CheckoutService
from ..business.customer_service import CustomerService
from ..business.interaction_service import InteractionService
from ..business.inventory_service import InventoryService
from ..business.order_service import OrderService
from ..business.payment_service import PaymentService
from ..business.product_service import ProductService
from ..business.promotion_service import PromotionService
from ..business.recommendation_service import RecommendationService
from ..business.report_service import ReportService
from ..business.search_service import SearchService
from ..business.restock_service import RestockService
from ..business.review_service import ReviewService
from ..business.shipping_service import ShippingService
from ..business.support_service import SupportService
from ..ai.runtime import AiRuntime
from ..persistence.repositories import (
    AccountRepository, AddressRepository, CartRepository, CategoryRepository, CustomerRepository,
    InteractionRepository, InventoryRepository, OrderRepository, PaymentRepository, ProductRepository,
    PromotionRepository, ReportRepository, RestockRepository, ReviewRepository, ShipmentRepository,
    SupplierRepository, SupportRepository,
)


@dataclass
class Services:
    auth: AuthService
    accounts: AccountService
    customers: CustomerService
    catalog: CatalogService
    products: ProductService
    promotions: PromotionService
    carts: CartService
    checkout: CheckoutService
    orders: OrderService
    payments: PaymentService
    shipping: ShippingService
    inventory: InventoryService
    restock: RestockService
    reviews: ReviewService
    support: SupportService
    interactions: InteractionService
    recommendations: RecommendationService
    reports: ReportService
    search: SearchService
    chat: ChatService


def build_services(s, ai: AiRuntime | None = None) -> Services:
    account_repo, customer_repo, address_repo = AccountRepository(s), CustomerRepository(s), AddressRepository(s)
    product_repo, category_repo, inv_repo = ProductRepository(s), CategoryRepository(s), InventoryRepository(s)
    cart_repo, order_repo, pay_repo = CartRepository(s), OrderRepository(s), PaymentRepository(s)
    promo_repo, review_repo, inter_repo = PromotionRepository(s), ReviewRepository(s), InteractionRepository(s)
    orders = OrderService(s, order_repo, inv_repo, reviews=review_repo)
    inventory = InventoryService(s, inv_repo)
    products = ProductService(s, product_repo, review_repo)
    search = SearchService(s, product_repo, products, ai)
    return Services(
        auth=AuthService(s, account_repo, customer_repo),
        accounts=AccountService(s, account_repo),
        customers=CustomerService(s, customer_repo, address_repo),
        catalog=CatalogService(s, product_repo, category_repo, inv_repo),
        products=products,
        promotions=PromotionService(s, promo_repo),
        carts=CartService(s, cart_repo, product_repo, inter_repo),
        checkout=CheckoutService(s, cart_repo, address_repo, promo_repo, inv_repo, order_repo,
                                 interactions=inter_repo),
        orders=orders,
        payments=PaymentService(s, pay_repo, order_repo, orders),
        shipping=ShippingService(s, order_repo, ShipmentRepository(s), orders),
        inventory=inventory,
        restock=RestockService(s, RestockRepository(s), SupplierRepository(s), product_repo, inventory),
        reviews=ReviewService(s, review_repo, order_repo),
        support=SupportService(s, SupportRepository(s), order_repo),
        interactions=InteractionService(s, inter_repo, product_repo),
        recommendations=RecommendationService(s, product_repo, inter_repo, order_repo),
        reports=ReportService(s, ReportRepository(s), inv_repo, inter_repo),
        search=search,
        chat=ChatService(s, search, promo_repo, order_repo, ai),
    )
