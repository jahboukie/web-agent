from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

Base = declarative_base()

class DatabaseConfig:
    def __init__(self, database_url: str, async_database_url: str):
        self.database_url = database_url
        self.async_database_url = async_database_url
        
        # Sync engine for migrations and admin tasks
        self.engine = create_engine(database_url, echo=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Async engine for application runtime
        self.async_engine = create_async_engine(async_database_url, echo=True)
        self.AsyncSessionLocal = sessionmaker(
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            bind=self.async_engine
        )

    async def get_async_session(self) -> AsyncSession:
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()