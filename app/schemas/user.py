from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_validator


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: str | None = Field(None, max_length=255)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, values: Any, **kwargs: Any) -> str:
        if "password" in values.data and v != values.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=100)
    full_name: str | None = Field(None, max_length=255)
    preferences: dict[str, Any] | None = None
    is_active: bool | None = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v: str, values: Any, **kwargs: Any) -> str:
        if "new_password" in values.data and v != values.data["new_password"]:
            raise ValueError("New passwords do not match")
        return v


class User(UserBase):
    id: int
    is_superuser: bool = False
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    preferences: dict[str, Any] = {}
    api_rate_limit: int = 100

    # Enterprise features
    employee_id: str | None = None
    department: str | None = None
    job_title: str | None = None
    manager_user_id: int | None = None
    sso_provider: str | None = None
    sso_user_id: str | None = None
    sso_attributes: dict[str, Any] = {}
    mfa_enabled: bool = False
    trust_score: dict[str, Any] = {}
    risk_profile: dict[str, Any] = {}
    data_classification: str = "internal"
    consent_given_at: datetime | None = None
    gdpr_consent: bool = False

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: str | None = None
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
    last_task_at: datetime | None = None
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
    notification_email: EmailStr | None = None
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
    usage_history: list[dict[str, Any]] = []


class UserRegistrationRequest(UserCreate):
    accept_terms: bool = True
    marketing_consent: bool = False

    @field_validator("accept_terms")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms of service")
        return v


class EnterpriseUserCreate(UserBase):
    """Enterprise user creation with SSO and organizational data."""

    password: str | None = Field(None, min_length=8, max_length=128)
    employee_id: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=255)
    manager_user_id: int | None = None
    sso_provider: str | None = Field(None, max_length=100)
    sso_user_id: str | None = Field(None, max_length=255)
    sso_attributes: dict[str, Any] = Field(default_factory=dict)
    data_classification: str = Field(default="internal", max_length=50)
    gdpr_consent: bool = False
    tenant_id: int | None = None
    role_ids: list[int] = Field(default_factory=list)


class EnterpriseUserUpdate(BaseModel):
    """Enterprise user update with organizational and security fields."""

    full_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    employee_id: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=255)
    manager_user_id: int | None = None
    preferences: dict[str, Any] | None = None
    api_rate_limit: int | None = Field(None, ge=1)
    mfa_enabled: bool | None = None
    data_classification: str | None = Field(None, max_length=50)
    gdpr_consent: bool | None = None


class UserTenantRole(BaseModel):
    """User-tenant-role association."""

    user_id: int
    tenant_id: int
    role_id: int
    assigned_at: datetime
    assigned_by: int | None = None
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


class UserTenantRoleAssignment(BaseModel):
    """Request to assign roles to user in tenant."""

    user_id: int
    tenant_id: int
    role_ids: list[int]
    expires_at: datetime | None = None


# Enterprise Security Enhancements


class SecurityRole(str, Enum):
    """Enterprise security roles with hierarchical permissions."""

    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    AUTOMATION_MANAGER = "AUTOMATION_MANAGER"
    ANALYST = "ANALYST"
    AUDITOR = "AUDITOR"
    END_USER = "END_USER"


class ComplianceLevel(str, Enum):
    """Data classification levels for compliance."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"
    TOP_SECRET = "TOP_SECRET"


class ThreatLevel(str, Enum):
    """Risk assessment threat levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EnterpriseUserCreateSecure(UserCreate):
    """Enterprise user creation with security enhancements."""

    tenant_id: str | None = None
    security_role: SecurityRole = SecurityRole.END_USER
    department: str | None = None
    manager_email: EmailStr | None = None
    requires_2fa: bool = True
    compliance_level: ComplianceLevel = ComplianceLevel.INTERNAL
    allowed_ip_ranges: list[str] = []

    # Zero-knowledge encryption keys (generated client-side)
    encryption_public_key: bytes | None = None
    signing_public_key: bytes | None = None
    key_derivation_salt: bytes | None = None

    # Enterprise onboarding
    employment_start_date: datetime | None = None
    security_clearance_level: str | None = None
    background_check_completed: bool = False


class DeviceInfo(BaseModel):
    """Device information for Zero Trust verification."""

    device_id: str
    device_type: Literal["desktop", "mobile", "tablet", "server"]
    os_name: str
    os_version: str
    browser_name: str | None = None
    browser_version: str | None = None
    is_managed: bool = False
    is_encrypted: bool = False
    last_security_scan: datetime | None = None
    trust_level: ThreatLevel = ThreatLevel.MEDIUM
    device_fingerprint: str


class AccessContext(BaseModel):
    """Zero Trust access context for continuous verification."""

    ip_address: str
    geolocation: dict[str, Any]
    device_info: DeviceInfo
    network_type: Literal["corporate", "home", "public", "vpn"]
    time_of_access: datetime
    user_agent: str
    session_duration: int  # seconds
    previous_login_location: dict[str, Any] | None = None
    risk_score: float = 0.0
    threat_indicators: list[str] = []


class MFAMethod(BaseModel):
    """Multi-factor authentication method."""

    method_type: Literal["totp", "sms", "email", "hardware_key", "biometric"]
    is_primary: bool
    is_backup: bool
    created_at: datetime
    last_used_at: datetime | None = None
    failure_count: int = 0
    is_compromised: bool = False


class SecurityEvent(BaseModel):
    """Security event for continuous monitoring."""

    event_id: str
    event_type: str
    user_id: int
    tenant_id: str | None = None
    severity: ThreatLevel
    description: str
    source_ip: str
    user_agent: str
    access_context: AccessContext
    automated_response: str | None = None
    requires_investigation: bool = False
    mitigated: bool = False
    created_at: datetime


class EnterpriseUserProfile(UserProfile):
    """Enhanced user profile with enterprise security features."""

    tenant_id: str | None = None
    security_role: SecurityRole = SecurityRole.END_USER
    department: str | None = None
    manager_id: int | None = None

    # Zero Trust Security
    trust_score: dict[str, Any] = Field(
        default_factory=dict,
        description="Zero Trust score: 0.0 = no trust, 1.0 = full trust",
    )
    last_risk_assessment: datetime | None = None
    current_threat_level: ThreatLevel = ThreatLevel.LOW
    failed_login_attempts: int = 0
    account_locked_until: datetime | None = None

    # MFA and Authentication
    mfa_enabled: bool = True
    mfa_methods: list[MFAMethod] = []
    requires_password_change: bool = False
    password_last_changed: datetime | None = None

    # Access Controls
    allowed_ip_ranges: list[str] = []
    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 3

    # Compliance and Audit
    compliance_level: ComplianceLevel = ComplianceLevel.INTERNAL
    data_retention_days: int = 2555  # 7 years default
    consent_given_at: datetime | None = None
    gdpr_consent: bool = False
    hipaa_consent: bool = False

    # Zero-Knowledge Encryption
    encryption_key_id: str | None = None
    signing_key_id: str | None = None
    key_rotation_required: bool = False
    last_key_rotation: datetime | None = None

    # Security Monitoring
    recent_security_events: list[SecurityEvent] = []
    suspicious_activity_score: float = 0.0
    last_security_scan: datetime | None = None

    # Enterprise Features
    provisioned_by: str | None = None
    deprovisioned_at: datetime | None = None
    employment_status: Literal["active", "suspended", "terminated"] = "active"
    security_clearance_level: str | None = None


class ZeroTrustVerification(BaseModel):
    """Zero Trust continuous verification result."""

    user_id: int
    verification_id: str
    access_granted: bool
    trust_score: float
    risk_factors: list[str] = []
    required_actions: list[str] = []  # e.g., ["require_mfa", "verify_device"]
    session_restrictions: dict[str, Any] = {}  # time limits, IP restrictions, etc.
    next_verification_in: int = 3600  # seconds until next verification
    verified_at: datetime


class IncidentResponse(BaseModel):
    """Security incident response tracking."""

    incident_id: str
    incident_type: str
    severity: ThreatLevel
    affected_users: list[int] = []
    affected_resources: list[str] = []
    detected_at: datetime
    response_initiated_at: datetime | None = None
    contained_at: datetime | None = None
    resolved_at: datetime | None = None
    root_cause: str | None = None
    lessons_learned: str | None = None
    notification_sent: bool = False
    customer_impact: bool = False
    regulatory_reporting_required: bool = False
