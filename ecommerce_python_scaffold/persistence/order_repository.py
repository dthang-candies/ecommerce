"""Repository: truy cập và lưu trữ dữ liệu."""


class OrderRepository:
    def __init__(self, database=None):
        self.database = database

    def add(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def get(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def list_by_customer(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def unpaid_before(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError
