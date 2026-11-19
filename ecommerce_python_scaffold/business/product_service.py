"""Business layer: xử lý quy tắc nghiệp vụ."""


class ProductService:
    def __init__(self, **dependencies):
        self.dependencies = dependencies

    def search(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def get_detail(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError
