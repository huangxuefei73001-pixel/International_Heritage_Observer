from __future__ import annotations

from app.config import Settings
from app.database import Base, build_engine
import app.models  # noqa: F401


def main() -> None:
    settings = Settings()
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    print("Initialized web database tables.")


if __name__ == "__main__":
    main()
