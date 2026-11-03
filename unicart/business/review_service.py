from ..domain.models import Review
from ..persistence.repositories import OrderRepository, ReviewRepository
from .exceptions import BusinessError, Conflict, Forbidden, NotFound
from .transaction import transactional


class ReviewService:
    """UC-09 Submit Product Review (FR-12, BR-09): only delivered orders, once per product per order, 1..5 stars."""

    def __init__(self, session, reviews: ReviewRepository, orders: OrderRepository):
        self.session, self.reviews, self.orders = session, reviews, orders

    @transactional
    def create(self, customer_id: int, order_id: int, product_id: int, rating: int, comment: str | None) -> Review:
        order = self.orders.get(order_id)
        if order is None:
            raise NotFound("Đơn hàng không tồn tại")
        if order.customer_id != customer_id:
            raise Forbidden("Đây không phải đơn hàng của bạn")
        if order.status != "DELIVERED":
            raise BusinessError("Chỉ có thể đánh giá sản phẩm của đơn đã giao")
        if all(i.product_id != product_id for i in order.items):
            raise BusinessError("Sản phẩm không thuộc đơn hàng này")
        if self.reviews.exists(order_id, product_id):
            raise Conflict("Bạn đã đánh giá sản phẩm này trong đơn hàng này")
        review = Review(customer_id=customer_id, product_id=product_id, order_id=order_id,
                        rating=rating, comment=(comment or "").strip() or None)
        if not review.is_valid_rating():
            raise BusinessError("Số sao phải từ 1 đến 5")
        return self.reviews.add(review)
