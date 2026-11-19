"""Controller layer: nhận input và điều phối sang service."""


class OrderController:
    def __init__(self, service):
        self.service = service

    def place(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def mine(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def change_status(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def cancel(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError
