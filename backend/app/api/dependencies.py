from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import create_database_engine, create_session_factory


@lru_cache(maxsize=1)
def get_api_engine() -> Engine:
    return create_database_engine()


@lru_cache(maxsize=1)
def get_api_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_api_engine())


def get_db() -> Generator[Session, None, None]:
    session = get_api_session_factory()()
    try:
        yield session
    finally:
        session.close()
