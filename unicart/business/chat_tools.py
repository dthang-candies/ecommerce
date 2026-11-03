"""Tools of the shopping assistant. The model (or the rule engine) can only READ shop data through these functions.

Safety by construction:
- the customer is taken from the authenticated session, never from model arguments, so one customer can never reach
  another customer's order through the chatbot;
- nothing here writes to the database: a support request is only *proposed* and the customer confirms it in the UI;
- data given back to the model is a slim view (no address, phone or recipient name) and free text is truncated;
- every failure is returned as {"error": ...} so the model can explain it instead of the request crashing."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Callable

from .. import config
from ..domain.enums import OrderStatus
from ..domain.models import CustomerOrder, Product, Promotion
from ..persistence.repositories import OrderRepository, PromotionRepository
from .actor import Actor
from .chat_policy import TOPICS, policies
from .exceptions import BusinessError, NotFound
from .search_service import SearchService

MAX_PRODUCTS, MAX_ORDERS = 5, 5
STATUS_VI = {"PENDING_PAYMENT": "Chờ thanh toán", "PENDING": "Chờ xác nhận", "CONFIRMED": "Đã xác nhận",
             "PACKED": "Đã đóng gói", "SHIPPING": "Đang giao", "DELIVERED": "Đã giao", "CANCELLED": "Đã hủy"}
LOGIN_NEEDED = "Cần đăng nhập bằng tài khoản khách hàng để xem thông tin đơn hàng."

# Function declarations in Gemini's schema dialect.
_S, _N, _I, _B, _O = "STRING", "NUMBER", "INTEGER", "BOOLEAN", "OBJECT"
TOOL_DECLARATIONS = [
    {"name": "search_products",
     "description": "Tìm sản phẩm còn bán theo nhu cầu của khách (loại hàng, thương hiệu, màu, khoảng giá). Trả tối đa 5 sản phẩm.",
     "parameters": {"type": _O, "properties": {
         "query": {"type": _S, "description": "Cụm từ tìm kiếm tiếng Việt, ví dụ 'giày chạy bộ màu đen'"},
         "min_price": {"type": _N, "description": "Giá tối thiểu (VND), tùy chọn"},
         "max_price": {"type": _N, "description": "Giá tối đa (VND), tùy chọn"},
         "in_stock_only": {"type": _B, "description": "Chỉ lấy sản phẩm còn hàng"}}, "required": ["query"]}},
    {"name": "get_product_details",
     "description": "Xem giá, tồn kho, mô tả của một sản phẩm theo mã số.",
     "parameters": {"type": _O, "properties": {"product_id": {"type": _I}}, "required": ["product_id"]}},
    {"name": "list_active_promotions",
     "description": "Liệt kê các mã giảm giá đang còn hiệu lực hôm nay (kèm điều kiện đơn tối thiểu và hạn dùng).",
     "parameters": {"type": _O, "properties": {}}},
    {"name": "get_my_orders",
     "description": "Liệt kê các đơn hàng gần đây của khách đang đăng nhập (mới nhất trước).",
     "parameters": {"type": _O, "properties": {}}},
    {"name": "get_order_status",
     "description": "Xem trạng thái, thanh toán, vận chuyển và lịch sử của MỘT đơn hàng của khách đang đăng nhập.",
     "parameters": {"type": _O, "properties": {"order_id": {"type": _I}}, "required": ["order_id"]}},
    {"name": "get_shop_policy",
     "description": "Lấy chính sách chính thức của cửa hàng. topic: return (đổi trả), cancel (hủy đơn), shipping (vận chuyển), "
                    "payment (thanh toán), promotion (khuyến mại).",
     "parameters": {"type": _O, "properties": {"topic": {"type": _S, "enum": list(TOPICS)}}, "required": ["topic"]}},
    {"name": "check_return_eligibility",
     "description": "Kiểm tra một đơn của khách đang đăng nhập còn trong thời hạn đổi trả hay không.",
     "parameters": {"type": _O, "properties": {"order_id": {"type": _I}}, "required": ["order_id"]}},
    {"name": "propose_support_request",
     "description": "Soạn sẵn yêu cầu hỗ trợ/đổi trả để khách xem và bấm xác nhận. KHÔNG gửi gì cho đến khi khách bấm nút. "
                    "Chỉ gọi khi khách đã nói rõ muốn gửi yêu cầu.",
     "parameters": {"type": _O, "properties": {
         "content": {"type": _S, "description": "Nội dung yêu cầu viết ở ngôi thứ nhất, nêu lý do nếu khách đã nói"},
         "order_id": {"type": _I, "description": "Mã đơn liên quan, tùy chọn"}}, "required": ["content"]}},
]


@dataclass
class ChatCards:
    """Domain objects behind the answer: the UI draws them as cards, so prices shown to the shopper always come from
    the database and never from model-written text."""
    products: list[Product] = field(default_factory=list)
    promotions: list[Promotion] = field(default_factory=list)
    orders: list[CustomerOrder] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)


def _clip(text: str | None, n: int) -> str:
    return " ".join((text or "").split())[:n]


def _money(value) -> int:
    return int(Decimal(value))


def _vnd(value) -> str:
    return f"{_money(value):,}".replace(",", ".") + "đ"


def _as_int(value) -> int | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if 0 < n < 10**12 else None


def _as_price(value) -> Decimal | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return d if d >= 0 else None


def describe_promotion(p: Promotion) -> str:
    value = f"{int(p.discount_value)}%" if p.discount_type == "PERCENT" else _vnd(p.discount_value)
    minimum = f" cho đơn từ {_vnd(p.min_order_value)}" if p.min_order_value and p.min_order_value > 0 else ""
    return f"Giảm {value}{minimum}, dùng đến {p.end_at:%d/%m/%Y}"


class ChatToolbox:
    def __init__(self, search: SearchService, promotions: PromotionRepository, orders: OrderRepository,
                 actor: Actor | None, now: Callable[[], datetime] = datetime.now):
        self.search, self.promotions, self.orders = search, promotions, orders
        self.actor, self.now = actor, now
        self.cards = ChatCards()
        self._handlers = {
            "search_products": self.search_products, "get_product_details": self.get_product_details,
            "list_active_promotions": self.list_active_promotions, "get_my_orders": self.get_my_orders,
            "get_order_status": self.get_order_status, "get_shop_policy": self.get_shop_policy,
            "check_return_eligibility": self.check_return_eligibility,
            "propose_support_request": self.propose_support_request,
        }

    # ------------------------------------------------------------------ dispatch
    @property
    def customer_id(self) -> int | None:
        return self.actor.account_id if self.actor is not None and self.actor.role == "CUSTOMER" else None

    def call(self, name: str, args: dict) -> dict:
        handler = self._handlers.get(name)
        if handler is None:
            return {"error": f"Công cụ '{name}' không tồn tại"}
        try:
            return handler(**{k: v for k, v in (args if isinstance(args, dict) else {}).items()
                              if k in handler.__code__.co_varnames[1:handler.__code__.co_argcount]})
        except BusinessError as e:
            return {"error": e.message}
        except TypeError:
            return {"error": "Tham số không hợp lệ"}

    # ------------------------------------------------------------------ products
    def _product_view(self, p: Product, rating: tuple[float, int] | None = None) -> dict:
        qty = p.inventory.quantity if p.inventory else 0
        view = {"id": p.id, "name": p.name, "brand": p.brand, "category": p.category.name if p.category else None,
                "price_vnd": _money(p.price), "in_stock": qty > 0, "quantity": min(qty, 50)}
        if rating and rating[1]:
            view["rating"] = {"average": round(rating[0], 1), "count": rating[1]}
        return view

    def _add_product(self, p: Product) -> None:
        if p.id not in {x.id for x in self.cards.products} and len(self.cards.products) < MAX_PRODUCTS + 1:
            self.cards.products.append(p)

    def search_products(self, query: str = "", min_price=None, max_price=None, in_stock_only=False) -> dict:
        query = _clip(str(query), 100)
        if not query:
            return {"error": "Thiếu cụm từ tìm kiếm"}
        out = self.search.search(query, None, _as_price(min_price), _as_price(max_price), "relevance", 1, 8)
        items = [p for p in out.items if not in_stock_only or (p.inventory and p.inventory.quantity > 0)][:MAX_PRODUCTS]
        ratings = self.search.product_service.rating_summary([p.id for p in items])
        for p in items:
            self._add_product(p)
        result: dict = {"total_found": out.total, "products": [self._product_view(p, ratings.get(p.id)) for p in items]}
        if out.corrected:
            result["searched_instead_for"] = out.corrected
        if out.suggestion:
            result["did_you_mean"] = out.suggestion
        return result

    def get_product_details(self, product_id=None) -> dict:
        pid = _as_int(product_id)
        if pid is None:
            return {"error": "Mã sản phẩm không hợp lệ"}
        p = self.search.product_service.get_detail(pid)                 # hidden products are invisible (BR-01)
        self._add_product(p)
        rating = self.search.product_service.rating_summary([p.id]).get(p.id)
        return self._product_view(p, rating) | {"description": _clip(p.description, 300),
                                               "attributes": {str(k): _clip(str(v), 40) for k, v in list((p.attributes or {}).items())[:8]}}

    # ------------------------------------------------------------------ promotions & policy
    def list_active_promotions(self) -> dict:
        promos = self.promotions.active_at(self.now())
        self.cards.promotions[:] = promos
        return {"today": f"{self.now():%d/%m/%Y}",
                "note": "Đây là mã giảm giá áp dụng cho cả đơn hàng ở bước thanh toán, không phải giá giảm riêng của từng sản phẩm.",
                "promotions": [{"code": p.code, "description": describe_promotion(p), "min_order_vnd": _money(p.min_order_value),
                                "valid_until": f"{p.end_at:%d/%m/%Y}"} for p in promos]}

    def get_shop_policy(self, topic: str = "") -> dict:
        text = policies().get(str(topic))
        return {"topic": topic, "policy": text} if text else {"error": f"Chủ đề phải là một trong: {', '.join(TOPICS)}"}

    # ------------------------------------------------------------------ orders (customer only, own orders only)
    def _own_order(self, order_id) -> CustomerOrder:
        if self.customer_id is None:
            raise BusinessError(LOGIN_NEEDED)
        oid = _as_int(order_id)
        order = self.orders.get(oid) if oid else None
        if order is None or order.customer_id != self.customer_id:      # same answer for 'missing' and 'not yours'
            raise NotFound("Không tìm thấy đơn hàng này trong tài khoản của bạn")
        return order

    @staticmethod
    def _order_summary(o: CustomerOrder) -> dict:
        return {"order_id": o.id, "status": STATUS_VI.get(o.status, o.status), "created": f"{o.created_at:%d/%m/%Y}",
                "total_vnd": _money(o.total_amount), "item_count": o.item_count(),
                "items": [f"{i.quantity} x {_clip(i.product.name, 60)}" for i in o.items][:6]}

    def _delivered_at(self, o: CustomerOrder) -> datetime | None:
        times = [h.changed_at for h in o.history if h.to_status == OrderStatus.DELIVERED.value and h.changed_at]
        if times:
            return max(times)
        if o.shipment and o.shipment.delivery_date:
            return datetime.combine(o.shipment.delivery_date, datetime.min.time())
        return None

    def get_my_orders(self) -> dict:
        if self.customer_id is None:
            return {"error": LOGIN_NEEDED}
        orders = self.orders.list_by_customer(self.customer_id)[:MAX_ORDERS]
        self.cards.orders[:] = orders
        return {"orders": [self._order_summary(o) for o in orders], "shown": len(orders)}

    def get_order_status(self, order_id=None) -> dict:
        o = self._own_order(order_id)
        self.cards.orders[:] = [o]
        view = self._order_summary(o) | {
            "payment_method": "Thanh toán khi nhận hàng (COD)" if o.payment_method == "COD" else "Thanh toán trực tuyến",
            "payment_status": o.payment.status if o.payment else None,
            "can_cancel": o.can_be_cancelled(),
            "history": [{"status": STATUS_VI.get(h.to_status, h.to_status), "at": f"{h.changed_at:%d/%m/%Y %H:%M}"}
                        for h in sorted(o.history, key=lambda h: h.id)][-6:]}
        if o.shipment:
            view["shipment"] = {"carrier": o.shipment.carrier, "tracking_number": o.shipment.tracking_number,
                                "status": o.shipment.status,
                                "delivery_date": o.shipment.delivery_date.isoformat() if o.shipment.delivery_date else None}
        return view

    def check_return_eligibility(self, order_id=None) -> dict:
        o = self._own_order(order_id)
        self.cards.orders[:] = [o]
        base = {"order_id": o.id, "status": STATUS_VI.get(o.status, o.status), "return_window_days": config.RETURN_WINDOW_DAYS}
        if o.status == OrderStatus.CANCELLED.value:
            return base | {"eligible": False, "reason": "Đơn đã hủy nên không có hàng để đổi trả."}
        if o.status != OrderStatus.DELIVERED.value:
            return base | {"eligible": False, "can_cancel_instead": o.can_be_cancelled(),
                           "reason": "Đơn chưa được giao nên chưa thể đổi trả."
                                     + (" Khách có thể tự hủy đơn trong mục Đơn hàng của tôi." if o.can_be_cancelled() else "")}
        delivered = self._delivered_at(o)
        if delivered is None:
            return base | {"eligible": None, "reason": "Không xác định được ngày giao; hãy gửi yêu cầu hỗ trợ để nhân viên kiểm tra."}
        deadline = delivered + timedelta(days=config.RETURN_WINDOW_DAYS)
        ok = self.now() <= deadline
        return base | {"eligible": ok, "delivered_on": f"{delivered:%d/%m/%Y}", "deadline": f"{deadline:%d/%m/%Y}",
                       "reason": "Còn trong thời hạn đổi trả." if ok else "Đã quá thời hạn đổi trả theo chính sách."}

    def propose_support_request(self, content: str = "", order_id=None) -> dict:
        if self.customer_id is None:
            return {"error": LOGIN_NEEDED}
        content = _clip(str(content), 1000)
        if len(content) < 5:
            return {"error": "Nội dung yêu cầu quá ngắn"}
        oid = None
        if order_id not in (None, "", 0):
            oid = self._own_order(order_id).id
        self.cards.actions[:] = [{"type": "create_support_request", "content": content, "order_id": oid}]
        return {"status": "waiting_for_customer_confirmation",
                "note": "Đã hiện nút xác nhận cho khách. Yêu cầu CHƯA được gửi; chỉ gửi khi khách bấm nút."}
