"""Business layer: xử lý quy tắc nghiệp vụ."""


class InventoryService:
    def __init__(self, **dependencies):
        self.dependencies = dependencies

    def low_stock_report(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError

    def restock(self, *args, **kwargs):
        # TODO: implement business rules from the use cases.
        raise NotImplementedError
