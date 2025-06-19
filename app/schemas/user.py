from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    preferences: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)

    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class User(UserBase):
    id: int
    is_superuser: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    preferences: Dict[str, Any] = {}
    api_rate_limit: int = 100

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=128)
    remember_me: bool = False


class UserLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    refresh_token: str


class UserProfile(User):
    task_count: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_execution_time_seconds: int = 0
    last_task_at: Optional[datetime] = None
    account_creation_date: datetime
    subscription_tier: str = "free"
    api_calls_today: int = 0
    rate_limit_remaining: int = 100


class UserPreferences(BaseModel):
    default_timeout_seconds: int = Field(default=300, ge=30, le=3600)
    default_max_retries: int = Field(default=3, ge=0, le=10)
    screenshot_frequency: int = Field(default=5, ge=1, le=50)
    require_confirmation_for_purchases: bool = True
    require_confirmation_for_account_changes: bool = True
    enable_notifications: bool = True
    notification_email: Optional[EmailStr] = None
    timezone: str = "UTC"
    language: str = "en"
    theme: str = "light"


class UserApiUsage(BaseModel):
    user_id: int
    api_calls_today: int
    api_calls_this_month: int
    rate_limit: int
    rate_limit_remaining: int
    next_reset_at: datetime
    subscription_tier: str
    usage_history: List[Dict[str, Any]] = []


class UserRegistrationRequest(UserCreate):
    accept_terms: bool = True
    marketing_consent: bool = False

    @validator('accept_terms')
    def must_accept_terms(cls, v):
        if not v:
            raise ValueError('You must accept the terms of service')
        return v