"""Controller layer: nhận input và điều phối sang service."""


class ProductController:
    def __init__(self, service):
        self.service = service

    def search(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError

    def detail(self, *args, **kwargs):
        # TODO: validate input, call the corresponding service.
        raise NotImplementedError
