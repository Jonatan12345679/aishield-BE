from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

#  Session Factory 
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base class untuk semua model SQLAlchemy (models/*.py mewarisi ini)."""

    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency FastAPI untuk inject DB session per-request.
    Session otomatis ditutup setelah request selesai, walau terjadi error.

    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Buat semua tabel berdasarkan model yang sudah di-import.
    Cocok untuk development/demo. Untuk production sebaiknya pakai Alembic.

    """
    Base.metadata.create_all(bind=engine)