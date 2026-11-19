"""Controller layer: nhận input và điều phối sang service."""


class CartController:
    def __init__(self, service):
        self.service = service

    def add_item(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def view(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def update(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def remove(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError
