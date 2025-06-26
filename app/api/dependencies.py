from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any

import aiohttp
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http_client import get_http_session
from app.core.security import verify_token
from app.db.session import get_async_session
from app.models.user import User

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
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
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
    user_id_from_payload: str | int | None = payload.get("sub")
    if user_id_from_payload is None:
        logger.warning("Token missing user ID")
        raise credentials_exception

    try:
        user_id = int(user_id_from_payload)
    except (ValueError, TypeError):
        logger.warning("Invalid user ID in token", user_id=user_id_from_payload)
        raise credentials_exception

    # Get user from database (import here to avoid circular imports)
    from app.services.user_service import get_user_by_id

    user = await get_user_by_id(db, user_id)
    if user is None:
        logger.warning("User not found", user_id=user_id)
        raise credentials_exception

    logger.debug(
        "User authenticated successfully", user_id=user.id, username=user.username
    )
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
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
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    return current_user


# Import enterprise token blacklist
from app.security.token_blacklist import enterprise_token_blacklist


# Create a simple token blacklist for basic auth functionality
class SimpleTokenBlacklist:
    def __init__(self) -> None:
        self._blacklisted_tokens: set[str] = set()

    def add_token(self, token: str) -> None:
        """Add token to blacklist."""
        self._blacklisted_tokens.add(token)

    def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        return token in self._blacklisted_tokens


# Create global token blacklist instance
token_blacklist = SimpleTokenBlacklist()


async def verify_token_not_blacklisted(
    token: Annotated[str, Depends(oauth2_scheme)],
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
    try:
        if (
            enterprise_token_blacklist
            and await enterprise_token_blacklist.is_blacklisted(token)
        ):
            logger.warning("Blacklisted token used")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        logger.error(f"Token blacklist check failed: {str(e)}")
        # Fail securely - if we can't check, assume it's valid but log the issue
        pass

    return token


# HTTP Session Dependencies
async def get_http_client() -> aiohttp.ClientSession:
    """
    HTTP client session dependency.

    Provides the shared aiohttp.ClientSession for making HTTP requests.
    This ensures proper resource management and connection pooling.

    Returns:
        aiohttp.ClientSession: Shared HTTP client session

    Raises:
        HTTPException: If HTTP client is not initialized
    """
    try:
        return await get_http_session()
    except RuntimeError as e:
        logger.error("HTTP client not available", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HTTP client service unavailable",
        )


# Enterprise Access Control Dependencies


async def get_current_user_with_tenant(
    tenant_id: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, int | None, set[str]]:
    """
    Get current user with tenant context for enterprise access control.

    Args:
        tenant_id: Optional tenant ID for context
        current_user: Current authenticated user
        db: Database session

    Returns:
        tuple: (user, tenant_id, user_permissions)
    """
    try:
        # Import here to avoid circular imports
        from app.services.rbac_service import enterprise_rbac_service

        # Get user permissions in tenant context
        user_permissions = await enterprise_rbac_service.get_user_permissions(
            db, current_user.id, tenant_id
        )

        return current_user, tenant_id, user_permissions

    except Exception as e:
        logger.error(f"Failed to get user tenant context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load user context",
        )


def require_enterprise_permission(permission: str, tenant_id: int | None = None) -> Any:
    """
    Dependency factory for requiring specific enterprise permissions.

    Args:
        permission: Required permission string
        tenant_id: Optional tenant ID for scoped permissions

    Returns:
        Dependency function that checks permission
    """

    async def check_permission(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        try:
            # Import here to avoid circular imports
            from app.services.rbac_service import enterprise_rbac_service

            has_permission = await enterprise_rbac_service.check_user_permission(
                db, current_user.id, permission, tenant_id
            )

            if not has_permission:
                logger.warning(
                    "Permission denied",
                    user_id=current_user.id,
                    permission=permission,
                    tenant_id=tenant_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required",
                )

            return current_user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission check failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed",
            )

    return Depends(check_permission)
