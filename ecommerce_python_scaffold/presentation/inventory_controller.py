"""Controller layer: nhận input và điều phối sang service."""


class InventoryController:
    def __init__(self, service):
        self.service = service

    def low_stock(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def restock(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError
