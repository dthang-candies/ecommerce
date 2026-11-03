from __future__ import annotations

from ...domain.enums import RestockStatus
from ...domain.models import RestockRequest
from ...persistence.repositories import InventoryRepository, ProductRepository, RestockRepository, SupplierRepository
from ..exceptions import BusinessError, Conflict, InvalidTransition, NotFound
from ..inventory_service import InventoryService
from ..transaction import transactional


class RestockService:
    """UC-22 Manage Restocking (FR-31, BR-11). Stock only grows when a CONFIRMED request is RECEIVED."""

    def __init__(self, session, restocks: RestockRepository, suppliers: SupplierRepository,
                 products: ProductRepository, inventory_service: InventoryService):
        self.session, self.restocks, self.suppliers = session, restocks, suppliers
        self.products, self.inventory_service = products, inventory_service

    def list(self, status: str | None = None) -> list[RestockRequest]:
        return self.restocks.list(status)

    def suppliers_list(self):
        return self.suppliers.list()

    @transactional
    def create(self, product_id: int, supplier_id: int, quantity: int, staff_id: int) -> RestockRequest:
        if quantity <= 0:
            raise BusinessError("Số lượng phải lớn hơn 0")
        if self.products.get(product_id) is None:
            raise NotFound("Sản phẩm không tồn tại")
        if self.suppliers.get(supplier_id) is None:
            raise NotFound("Nhà cung cấp không tồn tại")
        if self.restocks.open_for_product(product_id):
            raise Conflict("Sản phẩm này đã có yêu cầu nhập hàng đang xử lý")
        return self.restocks.add(RestockRequest(product_id=product_id, supplier_id=supplier_id, quantity=quantity,
                                                status=RestockStatus.REQUESTED.value, created_by=staff_id))

    def _locked(self, request_id: int) -> RestockRequest:
        req = self.restocks.get(request_id, lock=True)
        if req is None:
            raise NotFound("Yêu cầu nhập hàng không tồn tại")
        return req

    @transactional
    def supplier_respond(self, request_id: int, accept: bool) -> RestockRequest:
        """Supplier actor (integration): confirm or reject a REQUESTED order."""
        req = self._locked(request_id)
        if req.status != RestockStatus.REQUESTED.value:
            raise InvalidTransition("Yêu cầu không ở trạng thái chờ nhà cung cấp xác nhận")
        req.confirm() if accept else setattr(req, "status", RestockStatus.REJECTED.value)
        return req

    @transactional
    def receive(self, request_id: int, staff_id: int) -> RestockRequest:
        req = self._locked(request_id)
        if req.status != RestockStatus.CONFIRMED.value:
            raise InvalidTransition("Chỉ nhập kho khi nhà cung cấp đã xác nhận")
        req.receive()
        self.inventory_service.restock(req.product_id, req.quantity, staff_id)   # nested: same session/transaction
        return req
