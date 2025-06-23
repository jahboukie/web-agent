from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_db,
    token_blacklist,
    verify_token_not_blacklisted,
)
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.models.user import User
from app.schemas.user import (
    Token,
    TokenRefresh,
    UserLoginResponse,
    UserPublic,
    UserRegistrationRequest,
)
from app.services.user_service import authenticate_user, create_user, update_last_login

logger = structlog.get_logger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


@router.post(
    "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserRegistrationRequest, db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.

    Creates a new user with the provided information and returns the user profile.
    Validates password strength and email uniqueness.
    """
    logger.info(
        "User registration attempt", email=user_data.email, username=user_data.username
    )

    try:
        # Create user in database
        user = await create_user(db, user_data)

        logger.info(
            "User registered successfully", user_id=user.id, username=user.username
        )

        # Return user profile (excluding sensitive data)
        return UserPublic.model_validate(user)

    except ValueError as e:
        logger.warning("User registration validation error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error during user registration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error",
        )


@router.post("/login", response_model=UserLoginResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return access tokens.

    Validates credentials and returns JWT access and refresh tokens.
    """
    logger.info("User login attempt", username=form_data.username)

    # Authenticate user
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning("Failed login attempt", username=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access and refresh tokens
    access_token_data = {"sub": str(user.id), "username": user.username}
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(access_token_data)

    # Update last login timestamp
    await update_last_login(db, user.id)

    logger.info("User logged in successfully", user_id=user.id, username=user.username)

    return UserLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user=UserPublic.model_validate(user),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Validates refresh token and issues new access token.
    """
    logger.debug("Token refresh attempt")

    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token, token_type="refresh")
    if payload is None:
        logger.warning("Invalid refresh token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID and verify user still exists
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Refresh token missing user ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    from app.services.user_service import get_user_by_id

    user = await get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        logger.warning(
            "User not found or inactive during token refresh", user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens
    access_token_data = {"sub": str(user.id), "username": user.username}
    new_access_token = create_access_token(access_token_data)
    new_refresh_token = create_refresh_token(access_token_data)

    logger.info("Token refreshed successfully", user_id=user.id)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(verify_token_not_blacklisted)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Logout user and invalidate tokens.

    Adds tokens to blacklist and logs logout event.
    """
    # Add token to blacklist
    token_blacklist.add_token(token)

    logger.info(
        "User logged out successfully",
        user_id=current_user.id,
        username=current_user.username,
    )

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserPublic)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get current authenticated user profile.

    Returns user information based on the provided JWT token.
    """
    logger.debug(
        "User profile requested",
        user_id=current_user.id,
        username=current_user.username,
    )

    return UserPublic.model_validate(current_user)
