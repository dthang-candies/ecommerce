"""Sandbox adapters for the external partners (payment gateway, carrier). They honour the same data contract
as a real provider, so replacing them only touches this module (NFR-16, scope assumption of Chapter 1)."""
import secrets
from dataclasses import dataclass
from decimal import Decimal

from ..domain.enums import PaymentChannel, PaymentStatus


@dataclass(frozen=True)
class GatewayResult:
    status: PaymentStatus
    transaction_id: str
    message: str


class SandboxPaymentGateway:
    """Receives (order id, amount, channel, opaque token) - never card numbers (NFR-05).
    A token that ends with '0000' is declined; anything else succeeds."""

    def charge(self, order_id: int, amount: Decimal, channel: PaymentChannel, token: str) -> GatewayResult:
        transaction_id = f"TXN-{order_id}-{secrets.token_hex(5).upper()}"
        if token.endswith("0000"):
            return GatewayResult(PaymentStatus.FAILED, transaction_id, "Giao dịch bị từ chối bởi ngân hàng phát hành")
        return GatewayResult(PaymentStatus.SUCCESS, transaction_id, "Thanh toán thành công")


class SandboxCarrier:
    name = "UniExpress"

    def create_waybill(self, order_id: int) -> str:
        return f"UCX{order_id:06d}{secrets.token_hex(3).upper()}"
