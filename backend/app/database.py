from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=None)
def build_engine(database_url: str):
    engine_kwargs = {"future": True}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **engine_kwargs)


@lru_cache(maxsize=None)
def build_session_factory(database_url: str):
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
