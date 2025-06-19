from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import structlog

from app.core.security import password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.config import settings

logger = structlog.get_logger(__name__)


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    Create a new user account.
    
    Args:
        db: Database session
        user_data: User creation data
        
    Returns:
        User: Created user instance
        
    Raises:
        ValueError: If email or username already exists
        Exception: For other database errors
    """
    logger.info("Creating new user", email=user_data.email, username=user_data.username)
    
    # Check if email already exists
    existing_email = await get_user_by_email(db, user_data.email)
    if existing_email:
        logger.warning("Email already exists", email=user_data.email)
        raise ValueError("Email already registered")
    
    # Check if username already exists
    existing_username = await get_user_by_username(db, user_data.username)
    if existing_username:
        logger.warning("Username already exists", username=user_data.username)
        raise ValueError("Username already taken")
    
    # Hash password
    hashed_password = password_hash(user_data.password)
    
    # Create user instance
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=user_data.is_active,
        api_rate_limit=settings.RATE_LIMIT_PER_MINUTE,
        preferences={}
    )
    
    try:
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        logger.info("User created successfully", user_id=db_user.id, username=db_user.username)
        return db_user
        
    except IntegrityError as e:
        await db.rollback()
        logger.error("Database integrity error during user creation", error=str(e))
        raise ValueError("User creation failed due to constraint violation")
    except Exception as e:
        await db.rollback()
        logger.error("Unexpected error during user creation", error=str(e))
        raise


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username/email and password.
    
    Args:
        db: Database session
        username: Username or email
        password: Plain text password
        
    Returns:
        User: Authenticated user or None if authentication fails
    """
    logger.debug("Authenticating user", username=username)
    
    # Try to find user by username first, then by email
    user = await get_user_by_username(db, username)
    if not user:
        user = await get_user_by_email(db, username)
    
    if not user:
        logger.warning("User not found during authentication", username=username)
        return None
    
    if not user.is_active:
        logger.warning("Inactive user attempted login", user_id=user.id, username=username)
        return None
    
    if not verify_password(password, user.hashed_password):
        logger.warning("Invalid password for user", user_id=user.id, username=username)
        return None
    
    logger.info("User authenticated successfully", user_id=user.id, username=user.username)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        User: User instance or None if not found
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user:
            logger.debug("User found by ID", user_id=user_id, username=user.username)
        else:
            logger.debug("User not found by ID", user_id=user_id)
            
        return user
    except Exception as e:
        logger.error("Error getting user by ID", user_id=user_id, error=str(e))
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email address.
    
    Args:
        db: Database session
        email: Email address
        
    Returns:
        User: User instance or None if not found
    """
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            logger.debug("User found by email", email=email, user_id=user.id)
        else:
            logger.debug("User not found by email", email=email)
            
        return user
    except Exception as e:
        logger.error("Error getting user by email", email=email, error=str(e))
        return None


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username.
    
    Args:
        db: Database session
        username: Username
        
    Returns:
        User: User instance or None if not found
    """
    try:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if user:
            logger.debug("User found by username", username=username, user_id=user.id)
        else:
            logger.debug("User not found by username", username=username)
            
        return user
    except Exception as e:
        logger.error("Error getting user by username", username=username, error=str(e))
        return None


async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[User]:
    """
    Update user information.
    
    Args:
        db: Database session
        user_id: User ID to update
        user_data: Updated user data
        
    Returns:
        User: Updated user instance or None if not found
    """
    logger.info("Updating user", user_id=user_id)
    
    user = await get_user_by_id(db, user_id)
    if not user:
        logger.warning("User not found for update", user_id=user_id)
        return None
    
    # Update fields if provided
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    try:
        await db.commit()
        await db.refresh(user)
        logger.info("User updated successfully", user_id=user_id)
        return user
    except Exception as e:
        await db.rollback()
        logger.error("Error updating user", user_id=user_id, error=str(e))
        raise


async def update_last_login(db: AsyncSession, user_id: int) -> None:
    """
    Update user's last login timestamp.
    
    Args:
        db: Database session
        user_id: User ID
    """
    try:
        user = await get_user_by_id(db, user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await db.commit()
            logger.debug("Last login updated", user_id=user_id)
    except Exception as e:
        await db.rollback()
        logger.error("Error updating last login", user_id=user_id, error=str(e))
