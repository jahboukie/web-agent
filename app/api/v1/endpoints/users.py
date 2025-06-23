from fastapi import APIRouter, HTTPException, status

from app.schemas.user import User, UserPreferences, UserProfile, UserUpdate

router = APIRouter()


@router.get("/profile", response_model=UserProfile)
async def get_user_profile():
    """Get current user's detailed profile with stats."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User profile not yet implemented",
    )


@router.put("/profile", response_model=User)
async def update_user_profile(user_update: UserUpdate):
    """Update user profile information."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User profile update not yet implemented",
    )


@router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences():
    """Get user's preferences and settings."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User preferences not yet implemented",
    )


@router.put("/preferences", response_model=UserPreferences)
async def update_user_preferences(preferences: UserPreferences):
    """Update user's preferences and settings."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User preferences update not yet implemented",
    )
