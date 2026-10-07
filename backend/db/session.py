from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from backend.core.config import settings
from backend.db.models import Base
from backend.core.logging import get_logger
from typing import AsyncGenerator

logger = get_logger(__name__)

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.database_url_sync,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()


async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def drop_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped")
