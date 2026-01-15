from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
import logging

from config import settings
from db_models import Base

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with Supabase PostgreSQL
engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Usage in FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database connection and verify tables exist.
    
    IMPORTANT: This does NOT create tables - they already exist in Supabase.
    This only verifies the connection and table structure.
    """
    try:
        # Test connection
        with engine.connect() as conn:
            logger.info("✅ Database connection successful")
            
        # Verify tables exist (DO NOT CREATE - they exist in Supabase)
        # This will raise an error if tables don't match the models
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        required_tables = ['customers', 'trips', 'stops']
        existing_tables = inspector.get_table_names()
        
        for table in required_tables:
            if table not in existing_tables:
                logger.error(f"❌ Required table '{table}' not found in database")
                raise Exception(f"Table '{table}' does not exist in Supabase database")
            else:
                logger.info(f"✅ Table '{table}' exists")
        
        logger.info("✅ Database initialization complete")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise


def close_db():
    """Close database connection pool"""
    engine.dispose()
    logger.info("Database connection pool closed")
