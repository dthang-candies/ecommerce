"""Repository: truy cập và lưu trữ dữ liệu."""


class InventoryRepository:
    def __init__(self, database=None):
        self.database = database

    def try_decrease(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def increase(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def log(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def low_stock(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError
