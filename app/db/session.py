from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Global async engine instance
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """
    Get or create the async database engine.

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    global _async_engine

    if _async_engine is None:
        logger.info(
            "Creating async database engine",
            url=settings.ASYNC_DATABASE_URL.split("@")[0] + "@***",
        )

        _async_engine = create_async_engine(
            settings.ASYNC_DATABASE_URL,
            echo=settings.DEBUG,  # Log SQL queries in debug mode
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
            poolclass=NullPool if "sqlite" in settings.ASYNC_DATABASE_URL else None,
        )

        logger.info("Async database engine created successfully")

    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session factory.

    Returns:
        async_sessionmaker: SQLAlchemy async session factory
    """
    global _async_session_factory

    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        logger.info("Async session factory created successfully")

    return _async_session_factory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    This is the main dependency function for FastAPI endpoints.
    Sessions are managed by the caller - no automatic commits.

    Yields:
        AsyncSession: Database session
    """
    session_factory = get_async_session_factory()
    if session_factory is None:
        raise RuntimeError("Session factory not initialized")

    async with session_factory() as session:
        try:
            logger.debug("Database session created")
            yield session
            # Note: No automatic commit - let the caller manage transactions
            logger.debug("Database session yielded successfully")
        except Exception as e:
            logger.error("Database session error, rolling back", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")
    return  # Add a return to satisfy mypy's check for generator exit


async def create_tables() -> None:
    """
    Create all database tables.

    This is primarily used for testing purposes.
    In production, use Alembic migrations instead.
    """
    from app.db.base import Base

    engine = get_async_engine()

    async with engine.begin() as conn:
        logger.info("Creating database tables")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def drop_tables() -> None:
    """
    Drop all database tables.

    This is primarily used for testing purposes.
    Use with caution in production environments.
    """
    from app.db.base import Base

    engine = get_async_engine()

    async with engine.begin() as conn:
        logger.warning("Dropping all database tables")
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")


async def check_database_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        async for session in get_async_session():
            # Simple query to test connection
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            logger.info("Database connection check successful")
            return True
        return False  # Should not be reached, but satisfies mypy
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False


async def close_async_engine() -> None:
    """
    Close the async database engine.

    This should be called during application shutdown.
    """
    global _async_engine

    if _async_engine is not None:
        logger.info("Closing async database engine")
        await _async_engine.dispose()
        _async_engine = None
        logger.info("Async database engine closed")
