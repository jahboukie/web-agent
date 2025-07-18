import os

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import create_user

logger = structlog.get_logger(__name__)


async def init_db(db: AsyncSession) -> None:
    """
    Initialize database with required data.

    Args:
        db: Database session
    """
    logger.info("Initializing database")

    # Create superuser if none exists
    await create_superuser(db)

    # Create test data in development
    if settings.ENVIRONMENT == "development":
        await create_test_data(db)

    logger.info("Database initialization completed")


async def create_superuser(db: AsyncSession) -> User:
    """
    Create initial superuser if none exists.

    Args:
        db: Database session

    Returns:
        User: Superuser instance
    """
    logger.info("Checking for existing superuser")

    # Check if any superuser exists
    result = await db.execute(select(User).where(User.is_superuser == True))
    existing_superuser = result.scalar_one_or_none()

    if existing_superuser:
        logger.info("Superuser already exists", user_id=existing_superuser.id)
        return existing_superuser

    # Create default superuser
    default_admin_password = os.getenv("WEBAGENT_ADMIN_PASSWORD", "Admin123!")
    superuser_data = UserCreate(
        email="admin@webagent.com",
        username="admin",
        password=default_admin_password,
        confirm_password=default_admin_password,
        full_name="WebAgent Administrator",
        is_active=True,
    )

    try:
        superuser = await create_user(db, superuser_data)

        # Set superuser flag
        superuser.is_superuser = True
        await db.commit()
        await db.refresh(superuser)

        logger.info("Superuser created successfully", user_id=superuser.id)
        return superuser

    except Exception as e:
        logger.error("Failed to create superuser", error=str(e))
        raise


async def create_test_data(db: AsyncSession) -> None:
    """
    Create test data for development environment.

    Args:
        db: Database session
    """
    logger.info("Creating test data for development")

    # Create test users
    default_test_password = os.getenv("WEBAGENT_TEST_PASSWORD", "Testpass123!")
    test_users = [
        {
            "email": "test1@example.com",
            "username": "testuser1",
            "password": default_test_password,
            "full_name": "Test User One",
        },
        {
            "email": "test2@example.com",
            "username": "testuser2",
            "password": default_test_password,
            "full_name": "Test User Two",
        },
    ]

    for user_data in test_users:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data["email"]))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            try:
                test_user_create = UserCreate(
                    email=user_data["email"],
                    username=user_data["username"],
                    password=user_data["password"],
                    confirm_password=user_data["password"],
                    full_name=user_data["full_name"],
                    is_active=True,
                )

                user = await create_user(db, test_user_create)
                logger.info(
                    "Test user created", user_id=user.id, username=user.username
                )

            except Exception as e:
                logger.warning(
                    "Failed to create test user", email=user_data["email"], error=str(e)
                )
        else:
            logger.debug("Test user already exists", email=user_data["email"])

    logger.info("Test data creation completed")


async def check_database_health(db: AsyncSession) -> dict:
    """
    Check database health and return status information.

    Args:
        db: Database session

    Returns:
        dict: Health status information
    """
    try:
        # Test basic query
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        # Count users
        from sqlalchemy import func

        user_count_result = await db.execute(select(func.count(User.id)))
        user_count = user_count_result.scalar()

        # Check for superuser
        superuser_result = await db.execute(
            select(User).where(User.is_superuser == True)
        )
        has_superuser = superuser_result.scalar_one_or_none() is not None

        health_status = {
            "status": "healthy",
            "database_connection": True,
            "user_count": user_count,
            "has_superuser": has_superuser,
            "environment": settings.ENVIRONMENT,
        }

        logger.debug("Database health check completed", **health_status)
        return health_status

    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "database_connection": False,
            "error": str(e),
            "environment": settings.ENVIRONMENT,
        }
