from __future__ import annotations

from functools import lru_cache
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from .config import Settings
from .database import build_session_factory


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_db_session(settings: Settings = Depends(get_settings)) -> Generator[Session, None, None]:
    session_factory = build_session_factory(settings.database_url)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
