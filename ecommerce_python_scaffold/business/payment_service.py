"""Business layer: xử lý quy tắc nghiệp vụ."""


class PaymentService:
    def __init__(self, **dependencies):
        self.dependencies = dependencies

    def handle_callback(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError
