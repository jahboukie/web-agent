from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum
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


class EnterpriseUserCreate(UserCreate):
    """Enterprise user creation with security enhancements."""
    
    tenant_id: Optional[str] = None
    security_role: SecurityRole = SecurityRole.END_USER
    department: Optional[str] = None
    manager_email: Optional[EmailStr] = None
    requires_2fa: bool = True
    compliance_level: ComplianceLevel = ComplianceLevel.INTERNAL
    allowed_ip_ranges: List[str] = []
    
    # Zero-knowledge encryption keys (generated client-side)
    encryption_public_key: Optional[bytes] = None
    signing_public_key: Optional[bytes] = None
    key_derivation_salt: Optional[bytes] = None
    
    # Enterprise onboarding
    employment_start_date: Optional[datetime] = None
    security_clearance_level: Optional[str] = None
    background_check_completed: bool = False


class DeviceInfo(BaseModel):
    """Device information for Zero Trust verification."""
    
    device_id: str
    device_type: Literal["desktop", "mobile", "tablet", "server"]
    os_name: str
    os_version: str
    browser_name: Optional[str] = None
    browser_version: Optional[str] = None
    is_managed: bool = False
    is_encrypted: bool = False
    last_security_scan: Optional[datetime] = None
    trust_level: ThreatLevel = ThreatLevel.MEDIUM
    device_fingerprint: str
    

class AccessContext(BaseModel):
    """Zero Trust access context for continuous verification."""
    
    ip_address: str
    geolocation: Dict[str, Any]
    device_info: DeviceInfo
    network_type: Literal["corporate", "home", "public", "vpn"]
    time_of_access: datetime
    user_agent: str
    session_duration: int  # seconds
    previous_login_location: Optional[Dict[str, Any]] = None
    risk_score: float = 0.0
    threat_indicators: List[str] = []
    

class MFAMethod(BaseModel):
    """Multi-factor authentication method."""
    
    method_type: Literal["totp", "sms", "email", "hardware_key", "biometric"]
    is_primary: bool
    is_backup: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    failure_count: int = 0
    is_compromised: bool = False
    

class SecurityEvent(BaseModel):
    """Security event for continuous monitoring."""
    
    event_id: str
    event_type: str
    user_id: int
    tenant_id: Optional[str] = None
    severity: ThreatLevel
    description: str
    source_ip: str
    user_agent: str
    access_context: AccessContext
    automated_response: Optional[str] = None
    requires_investigation: bool = False
    mitigated: bool = False
    created_at: datetime
    

class EnterpriseUserProfile(UserProfile):
    """Enhanced user profile with enterprise security features."""
    
    tenant_id: Optional[str] = None
    security_role: SecurityRole = SecurityRole.END_USER
    department: Optional[str] = None
    manager_id: Optional[int] = None
    
    # Zero Trust Security
    trust_score: float = 0.5  # 0.0 = no trust, 1.0 = full trust
    last_risk_assessment: Optional[datetime] = None
    current_threat_level: ThreatLevel = ThreatLevel.LOW
    failed_login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    
    # MFA and Authentication
    mfa_enabled: bool = True
    mfa_methods: List[MFAMethod] = []
    requires_password_change: bool = False
    password_last_changed: Optional[datetime] = None
    
    # Access Controls
    allowed_ip_ranges: List[str] = []
    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 3
    
    # Compliance and Audit
    compliance_level: ComplianceLevel = ComplianceLevel.INTERNAL
    data_retention_days: int = 2555  # 7 years default
    consent_given_at: Optional[datetime] = None
    gdpr_consent: bool = False
    hipaa_consent: bool = False
    
    # Zero-Knowledge Encryption
    encryption_key_id: Optional[str] = None
    signing_key_id: Optional[str] = None
    key_rotation_required: bool = False
    last_key_rotation: Optional[datetime] = None
    
    # Security Monitoring
    recent_security_events: List[SecurityEvent] = []
    suspicious_activity_score: float = 0.0
    last_security_scan: Optional[datetime] = None
    
    # Enterprise Features
    provisioned_by: Optional[str] = None
    deprovisioned_at: Optional[datetime] = None
    employment_status: Literal["active", "suspended", "terminated"] = "active"
    security_clearance_level: Optional[str] = None
    

class ZeroTrustVerification(BaseModel):
    """Zero Trust continuous verification result."""
    
    user_id: int
    verification_id: str
    access_granted: bool
    trust_score: float
    risk_factors: List[str] = []
    required_actions: List[str] = []  # e.g., ["require_mfa", "verify_device"]
    session_restrictions: Dict[str, Any] = {}  # time limits, IP restrictions, etc.
    next_verification_in: int = 3600  # seconds until next verification
    verified_at: datetime
    

class IncidentResponse(BaseModel):
    """Security incident response tracking."""
    
    incident_id: str
    incident_type: str
    severity: ThreatLevel
    affected_users: List[int] = []
    affected_resources: List[str] = []
    detected_at: datetime
    response_initiated_at: Optional[datetime] = None
    contained_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    lessons_learned: Optional[str] = None
    notification_sent: bool = False
    customer_impact: bool = False
    regulatory_reporting_required: bool = False