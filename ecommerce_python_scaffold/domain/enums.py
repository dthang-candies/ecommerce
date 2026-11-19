from enum import Enum


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PACKED = "PACKED"
    SHIPPING = "SHIPPING"
    DELIVERED = "DELIVERED"


class PaymentMethod(str, Enum):
    COD = "COD"
    CARD = "CARD"


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"


class DiscountType(str, Enum):
    PERCENT = "PERCENT"
    AMOUNT = "AMOUNT"


class MovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    RETURN = "RETURN"
    ADJUST = "ADJUST"


class RestockStatus(str, Enum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    RECEIVED = "RECEIVED"
    REJECTED = "REJECTED"
