from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from ui_server.config import settings

engine = create_engine(settings.postgres_url, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI."""
    with get_db_context() as db:
        yield db


@contextmanager
def get_db_context() -> Session:
    """Context manager for DB sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
