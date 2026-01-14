# database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./scrapper_applicaton.db"  # SQLite for local development

# Database setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy models
Base = declarative_base()


# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database tables
def init_db():
    """Create all database tables"""
    from model import user, llm_provider
    Base.metadata.create_all(bind=engine)