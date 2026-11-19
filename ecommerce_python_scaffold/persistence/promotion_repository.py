"""Repository: truy cập và lưu trữ dữ liệu."""


class PromotionRepository:
    def __init__(self, database=None):
        self.database = database

    def find_by_code(self, *args, **kwargs):
        # TODO: implement query using the selected database/ORM.
        raise NotImplementedError
