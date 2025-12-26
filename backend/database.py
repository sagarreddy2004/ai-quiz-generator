# backend/database.py
import os
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env (example: postgresql://user:pass@localhost:5432/quizdb)")

# Create engine
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)

# Declarative base
Base = declarative_base()

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1024), nullable=False)
    title = Column(String(512), nullable=True)
    date_generated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    scraped_content = Column(Text, nullable=True)
    full_quiz_data = Column(Text, nullable=False)

    def __repr__(self):
        return f"<Quiz id={self.id} title={self.title!r} url={self.url!r}>"

def create_tables():
    """Create DB tables (if not present)."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_tables()
    print("Tables created (if not existing).")
