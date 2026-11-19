"""Business layer: xử lý quy tắc nghiệp vụ."""


class CartService:
    def __init__(self, **dependencies):
        self.dependencies = dependencies

    def view(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def add_item(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def update_quantity(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def remove_item(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError
