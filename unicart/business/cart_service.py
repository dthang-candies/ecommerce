from ..domain.enums import EventType
from ..domain.models import Cart, InteractionLog
from ..persistence.repositories import CartRepository, InteractionRepository, ProductRepository
from .exceptions import BusinessError, NotFound, OutOfStock
from .transaction import transactional


class CartService:
    """UC-05 Manage Shopping Cart. A cart item never exceeds the available stock (BR-02, BR-03, FR-05)."""

    def __init__(self, session, carts: CartRepository, products: ProductRepository,
                 interactions: InteractionRepository | None = None):
        self.session, self.carts, self.products, self.interactions = session, carts, products, interactions

    def _cart(self, customer_id: int) -> Cart:
        cart = self.carts.get_by_customer(customer_id)
        if cart is None:
            cart = Cart(customer_id=customer_id)
            self.session.add(cart)
            self.session.flush()
        return cart

    def view(self, customer_id: int) -> Cart:
        return self._cart(customer_id)

    @transactional
    def add_item(self, customer_id: int, product_id: int, qty: int, source: str | None = None,
                 track: bool = True) -> Cart:
        """`source` is the recommendation placement the click came from (if any), kept for FR-18 attribution."""
        if qty <= 0:
            raise BusinessError("Số lượng phải lớn hơn 0")
        product = self.products.get(product_id)
        if product is None or not product.is_visible():
            raise NotFound("Sản phẩm không tồn tại")
        cart = self._cart(customer_id)
        already = next((i.quantity for i in cart.items if i.product_id == product_id), 0)
        if not product.in_stock(already + qty):
            left = product.inventory.quantity if product.inventory else 0
            raise OutOfStock("Sản phẩm đã hết hàng" if left == 0 else f"Chỉ còn {left} sản phẩm trong kho")
        cart.add_item(product, qty)
        if track and self.interactions is not None:
            self.interactions.add(InteractionLog(customer_id=customer_id, product_id=product_id,
                                                 event_type=EventType.ADD_TO_CART.value,
                                                 keyword=f"rec:{source[:40]}" if source else None))
        return cart

    @transactional
    def update_quantity(self, customer_id: int, product_id: int, qty: int) -> Cart:
        cart = self._cart(customer_id)
        if all(i.product_id != product_id for i in cart.items):
            raise NotFound("Sản phẩm không có trong giỏ hàng")
        product = self.products.get(product_id)
        if qty > 0 and not product.in_stock(qty):
            left = product.inventory.quantity if product.inventory else 0
            raise OutOfStock("Sản phẩm đã hết hàng" if left == 0 else f"Chỉ còn {left} sản phẩm trong kho")
        cart.update_quantity(product_id, qty)
        return cart

    @transactional
    def remove_item(self, customer_id: int, product_id: int) -> Cart:
        cart = self._cart(customer_id)
        cart.remove_item(product_id)
        return cart
