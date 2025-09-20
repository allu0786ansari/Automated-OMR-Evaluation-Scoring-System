# backend/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from . import models  # noqa: F401
from ..core.config import settings
from contextlib import contextmanager

# Using SQLAlchemy (synchronous engine). We'll wrap blocking calls with asyncio.to_thread in CRUD.
engine = create_engine(settings.SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_db():
    """
    Dependency for FastAPI. Use like:
    with get_db() as db:
        ...
    In FastAPI endpoints we depend on this, but our CRUD wraps blocking ops.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
