from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = "sqlite:///./abc_shop.db"  # TODO: đổi sang DB thật


class Database:
    def __init__(self, url: str = DATABASE_URL):
        self._engine = create_engine(url)
        self._session_factory = sessionmaker(bind=self._engine)

    def new_session(self) -> Session:
        return self._session_factory()
