class BusinessError(Exception):
    """Base class of rule violations. http_status is used by the presentation layer."""
    http_status = 400
    code = "BUSINESS_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(BusinessError):
    http_status, code = 404, "NOT_FOUND"


class Forbidden(BusinessError):
    http_status, code = 403, "FORBIDDEN"


class OutOfStock(BusinessError):
    http_status, code = 409, "OUT_OF_STOCK"


class InvalidTransition(BusinessError):
    http_status, code = 409, "INVALID_TRANSITION"


class Unauthorized(BusinessError):
    http_status, code = 401, "UNAUTHENTICATED"


class Conflict(BusinessError):
    http_status, code = 409, "CONFLICT"


class ServiceUnavailable(BusinessError):
    http_status, code = 503, "AI_UNAVAILABLE"
