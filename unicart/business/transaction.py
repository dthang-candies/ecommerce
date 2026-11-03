"""Every public service method is one database transaction: commit on success, rollback on any error."""
from functools import wraps


def transactional(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            result = method(self, *args, **kwargs)
            self.session.commit()
            return result
        except Exception:
            self.session.rollback()
            raise
    return wrapper
