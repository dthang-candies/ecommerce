"""Repository: truy cập và lưu trữ dữ liệu."""


class PaymentRepository:
    def __init__(self, database=None):
        self.database = database

    def by_order(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def by_transaction(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError
