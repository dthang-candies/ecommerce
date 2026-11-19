"""Business layer: xử lý quy tắc nghiệp vụ."""


class OrderService:
    def __init__(self, **dependencies):
        self.dependencies = dependencies

    def change_status(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def cancel(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def list_for_customer(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def expire_unpaid(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError
