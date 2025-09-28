from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings

# --- 1. Database Connection URL ---
# This uses the settings from your config.py file to build the connection string
DATABASE_URL = settings.DATABASE_URL

# --- 2. SQLAlchemy Engine ---
engine = create_engine(DATABASE_URL)

# --- 3. Session Factory ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 4. Declarative Base ---
# Base is DEFINED here. Other files (like models.py) will import it from this file.
Base = declarative_base()

# --- 5. Dependency for API Endpoints ---
def get_db():
    """
    A FastAPI dependency that provides a database session for a single API request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
