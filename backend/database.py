"""
Database Setup - Engine, Async Session & Base Model
PT BESTPROFIT FUTURES SURABAYA
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Fail-fast: jangan pernah memakai kredensial default untuk produksi.
# Wajib di-set via environment (docker-compose / .env).
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Example: postgresql+asyncpg://user:pass@host:5432/dbname"
    )

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency: yield an async database session."""
    async with async_session() as s:
        try:
            yield s
        finally:
            await s.close()
