"""Business layer: xử lý quy tắc nghiệp vụ."""


class CheckoutService:
    def __init__(self, **dependencies):
        self.dependencies = dependencies

    def place_order(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError
