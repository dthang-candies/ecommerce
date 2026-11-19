"""Repository: truy cập và lưu trữ dữ liệu."""


class ProductRepository:
    def __init__(self, database=None):
        self.database = database

    def get(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError

    def search(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError
