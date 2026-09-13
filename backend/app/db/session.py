import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL must be configured for persistent database access."
        )

    return database_url


def create_database_engine(
    database_url: str | None = None,
) -> Engine:
    return create_engine(
        database_url or get_database_url(),
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
