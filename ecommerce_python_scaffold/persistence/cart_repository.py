"""Repository: truy cập và lưu trữ dữ liệu."""


class CartRepository:
    def __init__(self, database=None):
        self.database = database

    def get_by_customer(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError
