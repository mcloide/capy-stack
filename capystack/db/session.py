"""
Database session management for CapyStack.

This module handles database connection, session management, and initialization
for the CapyStack application using SQLAlchemy.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from core.settings import get_config

config = get_config()

# Create engine
engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    echo=config.FLASK_ENV == 'development'
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
