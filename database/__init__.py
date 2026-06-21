"""
Database initialization and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from bot.config import DATABASE_URL

from .models import Base

# Create engine and session factory
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Session = scoped_session(SessionLocal)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

def get_db():
    """Get database session"""
    db = Session()
    try:
        yield db
    finally:
        db.close()

def close_db():
    """Close database session"""
    Session.remove()