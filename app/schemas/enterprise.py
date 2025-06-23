"""
Enterprise RBAC/ABAC and SSO schemas for WebAgent.

Comprehensive schemas for enterprise security features including:
- Multi-tenant organization management
- Role-Based Access Control (RBAC)
- Attribute-Based Access Control (ABAC)
- Single Sign-On (SSO) integration
- Zero Trust access sessions
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


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
    password_policy: dict[str, Any] = Field(default_factory=dict)
    data_region: str = Field(default="us-east-1", max_length=50)
    encryption_required: bool = True
    audit_retention_days: int = Field(default=2555, ge=30)
    admin_email: str = Field(max_length=255)
    billing_email: str | None = Field(None, max_length=255)
    support_contact: str | None = Field(None, max_length=255)


class EnterpriseTenantCreate(EnterpriseTenantBase):
    pass


class EnterpriseTenantUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    compliance_level: ComplianceLevel | None = None
    max_users: int | None = Field(None, ge=1)
    max_concurrent_sessions: int | None = Field(None, ge=1)
    api_rate_limit: int | None = Field(None, ge=100)
    enforce_sso: bool | None = None
    require_mfa: bool | None = None
    session_timeout_minutes: int | None = Field(None, ge=5, le=1440)
    password_policy: dict[str, Any] | None = None
    encryption_required: bool | None = None
    audit_retention_days: int | None = Field(None, ge=30)
    admin_email: str | None = Field(None, max_length=255)
    billing_email: str | None = Field(None, max_length=255)
    support_contact: str | None = Field(None, max_length=255)


class EnterpriseTenant(EnterpriseTenantBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# Enterprise Role Schemas


class EnterpriseRoleBase(BaseModel):
    role_id: str = Field(max_length=100)
    name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    description: str | None = None
    parent_role_id: int | None = None
    role_level: int = Field(default=0, ge=0)
    is_system_role: bool = True
    is_tenant_scoped: bool = False
    is_active: bool = True
    max_session_duration_hours: int = Field(default=8, ge=1, le=24)
    requires_approval: bool = False
    risk_level: ThreatLevel = ThreatLevel.LOW


class EnterpriseRoleCreate(EnterpriseRoleBase):
    permission_ids: list[int] = Field(default_factory=list)


class EnterpriseRoleUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    max_session_duration_hours: int | None = Field(None, ge=1, le=24)
    requires_approval: bool | None = None
    risk_level: ThreatLevel | None = None
    permission_ids: list[int] | None = None


class EnterpriseRole(EnterpriseRoleBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    created_by: int | None = None

    class Config:
        from_attributes = True


# Enterprise Permission Schemas


class EnterprisePermissionBase(BaseModel):
    permission_id: str = Field(max_length=100)
    name: str = Field(max_length=255)
    display_name: str = Field(max_length=255)
    description: str | None = None
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
    configuration: dict[str, Any] = Field(default_factory=dict)
    attribute_mapping: dict[str, str] = Field(default_factory=dict)
    role_mapping: dict[str, list[str]] = Field(default_factory=dict)
    require_signed_assertions: bool = True
    require_encrypted_assertions: bool = False
    session_timeout_minutes: int = Field(default=480, ge=5, le=1440)


class SSOConfigurationCreate(SSOConfigurationBase):
    tenant_id: int


class SSOConfigurationUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    is_primary: bool | None = None
    auto_provision_users: bool | None = None
    configuration: dict[str, Any] | None = None
    attribute_mapping: dict[str, str] | None = None
    role_mapping: dict[str, list[str]] | None = None
    require_signed_assertions: bool | None = None
    require_encrypted_assertions: bool | None = None
    session_timeout_minutes: int | None = Field(None, ge=5, le=1440)


class SSOConfiguration(SSOConfigurationBase):
    id: int
    tenant_id: int
    encryption_key_id: str
    created_at: datetime
    updated_at: datetime | None = None
    last_used_at: datetime | None = None

    class Config:
        from_attributes = True


# ABAC Policy Schemas


class ABACPolicyBase(BaseModel):
    policy_id: str = Field(max_length=100)
    name: str = Field(max_length=255)
    description: str | None = None
    effect: Literal["ALLOW", "DENY"]
    priority: int = Field(default=100, ge=1, le=1000)
    conditions: dict[str, Any] = Field(default_factory=dict)
    resources: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_system_policy: bool = False
    version: str = Field(default="1.0", max_length=20)


class ABACPolicyCreate(ABACPolicyBase):
    tenant_id: int | None = None


class ABACPolicyUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    effect: Literal["ALLOW", "DENY"] | None = None
    priority: int | None = Field(None, ge=1, le=1000)
    conditions: dict[str, Any] | None = None
    resources: list[str] | None = None
    actions: list[str] | None = None
    is_active: bool | None = None
    version: str | None = Field(None, max_length=20)


class ABACPolicy(ABACPolicyBase):
    id: int
    tenant_id: int | None = None
    evaluation_count: int = 0
    last_evaluated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    created_by: int | None = None

    class Config:
        from_attributes = True


# Access Session Schemas


class AccessSessionBase(BaseModel):
    session_id: str = Field(max_length=255)
    is_active: bool = True
    is_sso_session: bool = False
    sso_session_id: str | None = Field(None, max_length=255)
    device_fingerprint: str | None = Field(None, max_length=255)
    ip_address: str | None = Field(None, max_length=45)
    user_agent: str | None = Field(None, max_length=1000)
    geolocation: dict[str, Any] = Field(default_factory=dict)
    initial_trust_score: float = Field(default=1.0, ge=0.0, le=1.0)
    current_trust_score: float = Field(default=1.0, ge=0.0, le=1.0)
    risk_factors: list[str] = Field(default_factory=list)
    requires_mfa: bool = False
    requires_device_trust: bool = False


class AccessSessionCreate(AccessSessionBase):
    user_id: int
    tenant_id: int | None = None
    expires_at: datetime


class AccessSession(AccessSessionBase):
    id: int
    user_id: int
    tenant_id: int | None = None
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    last_verification_at: datetime
    mfa_verified_at: datetime | None = None
    device_trusted_at: datetime | None = None

    class Config:
        from_attributes = True
