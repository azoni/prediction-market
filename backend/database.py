import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

# Database URL - uses SQLite for local dev, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dumarket.db")

# Handle postgres:// vs postgresql:// (Render uses postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
