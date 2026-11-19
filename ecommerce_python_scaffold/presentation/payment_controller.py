"""Controller layer: nhận input và điều phối sang service."""


class PaymentController:
    def __init__(self, service):
        self.service = service

    def callback(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError
