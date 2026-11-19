class BusinessError(Exception):
    """Lỗi nghiệp vụ dùng chung."""
    pass


class NotFoundError(BusinessError):
    pass


class ValidationError(BusinessError):
    pass


class InsufficientStockError(BusinessError):
    pass
