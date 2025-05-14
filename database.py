from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import asyncio
from fastapi import HTTPException
from sqlalchemy import text
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Dependency to get DB session
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

# Function to test database connection
async def check_database_connection():
    try:
        # Try to create a connection
        async with engine.begin() as conn:
            # Execute a simple query using text() to create an executable statement
            result = await conn.execute(text("SELECT 1"))
            return {"status": "success", "message": "Connected to database successfully!"}
    except Exception as e:
        # Return error details if connection fails
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}