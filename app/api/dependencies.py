from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config import settings
from app.core.security import verify_token
from app.db.session import get_async_session

logger = structlog.get_logger(__name__)

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.

    Provides a clean database session for FastAPI endpoints.
    Handles transaction management appropriately for read/write operations.

    Yields:
        AsyncSession: Database session
    """
    async for session in get_async_session():
        yield session
        break  # Only get one session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    payload = verify_token(token, token_type="access")
    if payload is None:
        logger.warning("Invalid token provided")
        raise credentials_exception
    
    # Extract user ID from token
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        logger.warning("Token missing user ID")
        raise credentials_exception
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        logger.warning("Invalid user ID in token", user_id=user_id)
        raise credentials_exception
    
    # Get user from database (import here to avoid circular imports)
    from app.services.user_service import get_user_by_id
    user = await get_user_by_id(db, user_id)
    if user is None:
        logger.warning("User not found", user_id=user_id)
        raise credentials_exception

    logger.debug("User authenticated successfully", user_id=user.id, username=user.username)
    return user


async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    Get current active user (must be active).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        logger.warning("Inactive user attempted access", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return current_user


async def get_current_superuser(
    current_user = Depends(get_current_active_user)
):
    """
    Get current superuser (must be active superuser).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning("Non-superuser attempted admin access", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return current_user


class TokenBlacklist:
    """
    Simple in-memory token blacklist for logout functionality.
    In production, this should be replaced with Redis or database storage.
    """
    
    def __init__(self):
        self._blacklisted_tokens = set()
    
    def add_token(self, token: str) -> None:
        """Add token to blacklist."""
        self._blacklisted_tokens.add(token)
        logger.debug("Token added to blacklist")
    
    def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        return token in self._blacklisted_tokens
    
    def clear_expired_tokens(self) -> None:
        """Clear expired tokens from blacklist (placeholder for future implementation)."""
        # TODO: Implement token expiration cleanup
        pass


# Global token blacklist instance
token_blacklist = TokenBlacklist()


async def verify_token_not_blacklisted(
    token: str = Depends(oauth2_scheme)
) -> str:
    """
    Verify that token is not blacklisted.
    
    Args:
        token: JWT token to check
        
    Returns:
        str: Token if valid
        
    Raises:
        HTTPException: If token is blacklisted
    """
    if token_blacklist.is_blacklisted(token):
        logger.warning("Blacklisted token used")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token
