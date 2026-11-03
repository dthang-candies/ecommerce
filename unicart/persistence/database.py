from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .. import config


class Database:
    """Creates sessions. One session per request (presentation) or per test."""

    def __init__(self, url: str = config.DATABASE_URL):
        self.engine = create_engine(url, pool_pre_ping=True)
        self._factory = sessionmaker(self.engine, expire_on_commit=False)

    def new_session(self) -> Session:
        return self._factory()
