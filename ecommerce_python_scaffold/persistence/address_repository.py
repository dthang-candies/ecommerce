"""Repository: truy cập và lưu trữ dữ liệu."""


class AddressRepository:
    def __init__(self, database=None):
        self.database = database

    def get_for_customer(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError
