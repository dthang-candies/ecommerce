"""Enumerations of the design class diagram (section 4.3)."""
from enum import Enum


class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class OrderStatus(_StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PACKED = "PACKED"
    SHIPPING = "SHIPPING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentMethod(_StrEnum):
    COD = "COD"
    ONLINE = "ONLINE"


class PaymentChannel(_StrEnum):
    COD = "COD"
    WALLET = "WALLET"
    CARD = "CARD"


class PaymentStatus(_StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ShipmentStatus(_StrEnum):
    CREATED = "CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class LoyaltyTier(_StrEnum):
    NEW = "NEW"
    REGULAR = "REGULAR"
    VIP = "VIP"


class ProductStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"


class DiscountType(_StrEnum):
    PERCENT = "PERCENT"
    AMOUNT = "AMOUNT"


class MovementType(_StrEnum):
    IN = "IN"
    OUT = "OUT"
    RETURN = "RETURN"
    ADJUST = "ADJUST"


class SupportStatus(_StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class RestockStatus(_StrEnum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    RECEIVED = "RECEIVED"
    REJECTED = "REJECTED"


class EventType(_StrEnum):
    VIEW = "VIEW"
    SEARCH = "SEARCH"
    ADD_TO_CART = "ADD_TO_CART"
    PURCHASE = "PURCHASE"
    CLICK_REC = "CLICK_REC"
    REC_IMPRESSION = "REC_IMPRESSION"      # needed for CTR (formula 3.3)
