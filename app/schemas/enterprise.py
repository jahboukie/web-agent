"""
Enterprise RBAC/ABAC and SSO schemas for WebAgent.

Comprehensive schemas for enterprise security features including:
- Multi-tenant organization management
- Role-Based Access Control (RBAC)
- Attribute-Based Access Control (ABAC)
- Single Sign-On (SSO) integration
- Zero Trust access sessions
"""

from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class ThreatLevel(str, Enum):
    """Security threat levels for risk assessment."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceLevel(str, Enum):
    """Compliance levels for data classification."""
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PUBLIC = "public"


class SSOProtocol(str, Enum):
    """Supported SSO protocols."""
    SAML2 = "saml2"
    OPENID_CONNECT = "oidc"
    OAUTH2 = "oauth2"


class SSOProvider(str, Enum):
    """Supported SSO providers."""
    OKTA = "okta"
    AZURE_AD = "azure_ad"
    GOOGLE_WORKSPACE = "google_workspace"
    PING_IDENTITY = "ping_identity"
    AUTH0 = "auth0"
    ONELOGIN = "onelogin"
    ADFS = "adfs"
    GENERIC_SAML = "generic_saml"
    GENERIC_OIDC = "generic_oidc"


# Enterprise Tenant Schemas

class EnterpriseTenantBase(BaseModel):
    tenant_id: str = Field(max_length=100)
    name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    domain: str = Field(max_length=255)
    is_active: bool = True
    is_enterprise: bool = True
    compliance_level: ComplianceLevel = ComplianceLevel.INTERNAL
    subscription_tier: str = Field(default="enterprise", max_length=50)
    max_users: int = Field(default=1000, ge=1)
    max_concurrent_sessions: int = Field(default=100, ge=1)
    api_rate_limit: int = Field(default=10000, ge=100)
    enforce_sso: bool = True
    require_mfa: bool = True
    session_timeout_minutes: int = Field(default=480, ge=5, le=1440)
    password_policy: Dict[str, Any] = Field(default_factory=dict)
    data_region: str = Field(default="us-east-1", max_length=50)
    encryption_required: bool = True
    audit_retention_days: int = Field(default=2555, ge=30)
    admin_email: str = Field(max_length=255)
    billing_email: Optional[str] = Field(None, max_length=255)
    support_contact: Optional[str] = Field(None, max_length=255)


class EnterpriseTenantCreate(EnterpriseTenantBase):
    pass


class EnterpriseTenantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    compliance_level: Optional[ComplianceLevel] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_concurrent_sessions: Optional[int] = Field(None, ge=1)
    api_rate_limit: Optional[int] = Field(None, ge=100)
    enforce_sso: Optional[bool] = None
    require_mfa: Optional[bool] = None
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=1440)
    password_policy: Optional[Dict[str, Any]] = None
    encryption_required: Optional[bool] = None
    audit_retention_days: Optional[int] = Field(None, ge=30)
    admin_email: Optional[str] = Field(None, max_length=255)
    billing_email: Optional[str] = Field(None, max_length=255)
    support_contact: Optional[str] = Field(None, max_length=255)


class EnterpriseTenant(EnterpriseTenantBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Enterprise Role Schemas

class EnterpriseRoleBase(BaseModel):
    role_id: str = Field(max_length=100)
    name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    description: Optional[str] = None
    parent_role_id: Optional[int] = None
    role_level: int = Field(default=0, ge=0)
    is_system_role: bool = True
    is_tenant_scoped: bool = False
    is_active: bool = True
    max_session_duration_hours: int = Field(default=8, ge=1, le=24)
    requires_approval: bool = False
    risk_level: ThreatLevel = ThreatLevel.LOW


class EnterpriseRoleCreate(EnterpriseRoleBase):
    permission_ids: List[int] = Field(default_factory=list)


class EnterpriseRoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    max_session_duration_hours: Optional[int] = Field(None, ge=1, le=24)
    requires_approval: Optional[bool] = None
    risk_level: Optional[ThreatLevel] = None
    permission_ids: Optional[List[int]] = None


class EnterpriseRole(EnterpriseRoleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


# Enterprise Permission Schemas

class EnterprisePermissionBase(BaseModel):
    permission_id: str = Field(max_length=100)
    name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    description: Optional[str] = None
    category: str = Field(max_length=100)
    resource_type: str = Field(max_length=100)
    action: str = Field(max_length=100)
    is_system_permission: bool = True
    is_dangerous: bool = False
    risk_level: ThreatLevel = ThreatLevel.LOW


class EnterprisePermissionCreate(EnterprisePermissionBase):
    pass


class EnterprisePermission(EnterprisePermissionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# SSO Configuration Schemas

class SSOConfigurationBase(BaseModel):
    provider: SSOProvider
    protocol: SSOProtocol
    name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    is_active: bool = True
    is_primary: bool = False
    auto_provision_users: bool = True
    configuration: Dict[str, Any] = Field(default_factory=dict)
    attribute_mapping: Dict[str, str] = Field(default_factory=dict)
    role_mapping: Dict[str, List[str]] = Field(default_factory=dict)
    require_signed_assertions: bool = True
    require_encrypted_assertions: bool = False
    session_timeout_minutes: int = Field(default=480, ge=5, le=1440)


class SSOConfigurationCreate(SSOConfigurationBase):
    tenant_id: int


class SSOConfigurationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None
    auto_provision_users: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None
    attribute_mapping: Optional[Dict[str, str]] = None
    role_mapping: Optional[Dict[str, List[str]]] = None
    require_signed_assertions: Optional[bool] = None
    require_encrypted_assertions: Optional[bool] = None
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=1440)


class SSOConfiguration(SSOConfigurationBase):
    id: int
    tenant_id: int
    encryption_key_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ABAC Policy Schemas

class ABACPolicyBase(BaseModel):
    policy_id: str = Field(max_length=100)
    name: str = Field(max_length=255)
    description: Optional[str] = None
    effect: Literal["ALLOW", "DENY"]
    priority: int = Field(default=100, ge=1, le=1000)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    is_active: bool = True
    is_system_policy: bool = False
    version: str = Field(default="1.0", max_length=20)


class ABACPolicyCreate(ABACPolicyBase):
    tenant_id: Optional[int] = None


class ABACPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    effect: Optional[Literal["ALLOW", "DENY"]] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    conditions: Optional[Dict[str, Any]] = None
    resources: Optional[List[str]] = None
    actions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    version: Optional[str] = Field(None, max_length=20)


class ABACPolicy(ABACPolicyBase):
    id: int
    tenant_id: Optional[int] = None
    evaluation_count: int = 0
    last_evaluated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


# Access Session Schemas

class AccessSessionBase(BaseModel):
    session_id: str = Field(max_length=255)
    is_active: bool = True
    is_sso_session: bool = False
    sso_session_id: Optional[str] = Field(None, max_length=255)
    device_fingerprint: Optional[str] = Field(None, max_length=255)
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=1000)
    geolocation: Dict[str, Any] = Field(default_factory=dict)
    initial_trust_score: float = Field(default=1.0, ge=0.0, le=1.0)
    current_trust_score: float = Field(default=1.0, ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list)
    requires_mfa: bool = False
    requires_device_trust: bool = False


class AccessSessionCreate(AccessSessionBase):
    user_id: int
    tenant_id: Optional[int] = None
    expires_at: datetime


class AccessSession(AccessSessionBase):
    id: int
    user_id: int
    tenant_id: Optional[int] = None
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    last_verification_at: datetime
    mfa_verified_at: Optional[datetime] = None
    device_trusted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
