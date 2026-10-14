"""SQLAlchemy database session lifecycle. Run Alembic migrations before serving."""
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import get_settings

class Base(DeclarativeBase):
    pass

@lru_cache
def get_engine():
    url = get_settings().database_url
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, **kwargs)

def get_db():
    with Session(get_engine()) as session:
        yield session
