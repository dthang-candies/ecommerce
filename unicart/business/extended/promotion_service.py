from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from ...domain.enums import DiscountType
from ...domain.models import Promotion
from ...persistence.repositories import PromotionRepository
from ..exceptions import BusinessError, Conflict, NotFound
from ..transaction import transactional

audit = logging.getLogger("unicart.audit")


class PromotionService:
    """UC-11 Manage Promotions (FR-14, BR-05)."""

    def __init__(self, session, promotions: PromotionRepository):
        self.session, self.promotions = session, promotions

    def list(self) -> list[Promotion]:
        return self.promotions.list()

    def usage(self, promotion_id: int) -> int:
        return self.promotions.used_count(promotion_id)

    def _fill(self, p: Promotion, code, discount_type, discount_value, min_order_value, start_at, end_at, active):
        try:
            kind = DiscountType(discount_type)
            value, minimum = Decimal(str(discount_value)), Decimal(str(min_order_value or 0))
        except (ValueError, InvalidOperation):
            raise BusinessError("Dữ liệu khuyến mại không hợp lệ")
        if value <= 0 or minimum < 0:
            raise BusinessError("Giá trị giảm phải lớn hơn 0")
        if kind == DiscountType.PERCENT and value > 100:
            raise BusinessError("Phần trăm giảm tối đa là 100")
        if end_at <= start_at:
            raise BusinessError("Ngày kết thúc phải sau ngày bắt đầu")
        p.code, p.discount_type, p.discount_value = code.strip().upper(), kind.value, value
        p.min_order_value, p.start_at, p.end_at, p.active = minimum, start_at, end_at, bool(active)

    @transactional
    def create(self, admin_id: int, code: str, **fields) -> Promotion:
        code = code.strip().upper()
        if not code:
            raise BusinessError("Mã khuyến mại là bắt buộc")
        if self.promotions.find_by_code(code):
            raise Conflict("Mã khuyến mại đã tồn tại")
        p = Promotion()
        self._fill(p, code, **fields)
        self.promotions.add(p)
        audit.info("admin=%s created promotion=%s", admin_id, p.code)
        return p

    @transactional
    def update(self, admin_id: int, promotion_id: int, code: str, **fields) -> Promotion:
        p = self.promotions.get(promotion_id)
        if p is None:
            raise NotFound("Khuyến mại không tồn tại")
        other = self.promotions.find_by_code(code.strip().upper())
        if other and other.id != p.id:
            raise Conflict("Mã khuyến mại đã tồn tại")
        self._fill(p, code, **fields)
        audit.info("admin=%s updated promotion=%s", admin_id, p.code)
        return p

    @transactional
    def delete(self, admin_id: int, promotion_id: int) -> str:
        p = self.promotions.get(promotion_id)
        if p is None:
            raise NotFound("Khuyến mại không tồn tại")
        if self.promotions.used_count(promotion_id):       # used by orders: keep history, just switch off
            p.active = False
            return "DISABLED"
        self.promotions.delete(p)
        audit.info("admin=%s deleted promotion=%s", admin_id, p.code)
        return "DELETED"

    def check(self, code: str, subtotal: Decimal, now: datetime | None = None) -> Promotion:
        """Return the promotion if the code is valid for this subtotal, otherwise raise BusinessError (UC-06 A3)."""
        promo = self.promotions.find_by_code(code.strip().upper())
        if promo is None:
            raise BusinessError("Mã giảm giá không tồn tại")
        if not promo.active or (now or datetime.now()) > promo.end_at or (now or datetime.now()) < promo.start_at:
            raise BusinessError("Mã giảm giá đã hết hạn hoặc chưa có hiệu lực")
        if subtotal < promo.min_order_value:
            raise BusinessError(f"Đơn hàng tối thiểu {int(promo.min_order_value):,}đ để dùng mã này".replace(",", "."))
        return promo
