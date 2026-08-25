from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import make_url
from app.core.config import settings


from sqlalchemy.pool import NullPool

# Create async engine
# connect_args disables asyncpg prepared statement caching for Supabase pgBouncer pooler
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    future=True,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base for all models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get database session with proper rollback on error."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
