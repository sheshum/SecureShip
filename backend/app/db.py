import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost:5432/secureship")


def _to_psycopg_url(url: str) -> str:
    """SQLAlchemy needs the psycopg3 driver spelled out in the URL scheme."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_to_psycopg_url(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False)
