from ...domain.models import Address, Customer
from ...persistence.repositories import AddressRepository, CustomerRepository
from ..exceptions import BusinessError, NotFound
from ..transaction import transactional
from .validation import check_phone


class CustomerService:
    """UC-08 Manage Profile and delivery address book (FR-11)."""

    def __init__(self, session, customers: CustomerRepository, addresses: AddressRepository):
        self.session, self.customers, self.addresses = session, customers, addresses

    def profile(self, customer_id: int) -> Customer:
        c = self.customers.get(customer_id)
        if c is None:
            raise NotFound("Không tìm thấy hồ sơ khách hàng")
        return c

    @transactional
    def update_profile(self, customer_id: int, first_name: str, last_name: str,
                       middle_name: str | None, phone: str | None) -> Customer:
        c = self.profile(customer_id)
        if not first_name.strip() or not last_name.strip():
            raise BusinessError("Họ và tên là bắt buộc")
        c.first_name, c.last_name = first_name.strip(), last_name.strip()
        c.middle_name = (middle_name or "").strip() or None
        c.phone = check_phone(phone)
        return c

    def list_addresses(self, customer_id: int) -> list[Address]:
        return self.addresses.list_for_customer(customer_id)

    def _fill(self, a: Address, recipient, phone, street, district, city, post_code) -> None:
        if not recipient.strip() or not street.strip() or not city.strip():
            raise BusinessError("Người nhận, địa chỉ và thành phố là bắt buộc")
        a.recipient, a.street, a.city = recipient.strip(), street.strip(), city.strip()
        a.phone = check_phone(phone, required=True)
        a.district = (district or "").strip() or None
        a.post_code = (post_code or "").strip() or None

    @transactional
    def add_address(self, customer_id: int, recipient, phone, street, district, city, post_code,
                    is_default: bool) -> Address:
        a = Address(customer_id=customer_id, country="Viet Nam", is_default=False)
        self._fill(a, recipient, phone, street, district, city, post_code)
        first = not self.addresses.list_for_customer(customer_id)
        if is_default or first:
            self.addresses.clear_default(customer_id)
            a.is_default = True
        return self.addresses.add(a)

    @transactional
    def update_address(self, customer_id: int, address_id: int, recipient, phone, street, district, city,
                       post_code, is_default: bool) -> Address:
        a = self.addresses.get_for_customer(address_id, customer_id)
        if a is None:
            raise NotFound("Không tìm thấy địa chỉ")
        self._fill(a, recipient, phone, street, district, city, post_code)
        if is_default and not a.is_default:
            self.addresses.clear_default(customer_id)
            a.is_default = True
        return a

    @transactional
    def delete_address(self, customer_id: int, address_id: int) -> None:
        a = self.addresses.get_for_customer(address_id, customer_id)
        if a is None:
            raise NotFound("Không tìm thấy địa chỉ")
        was_default = a.is_default
        self.addresses.delete(a)
        self.session.flush()
        if was_default:                                   # keep one default when any address remains
            remaining = self.addresses.list_for_customer(customer_id)
            if remaining:
                remaining[0].is_default = True
