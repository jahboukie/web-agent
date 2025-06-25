# === FORCE UPDATE ===
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .user import User


class CredentialType(str, Enum):
    PASSWORD = "password"
    API_KEY = "api_key"
    OAUTH_TOKEN = "oauth_token"
    SAML_ASSERTION = "saml_assertion"


class AuditEventType(str, Enum):
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_LOGIN_FAILED = "user_login_failed"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"


class PermissionScope(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    OWNER = "owner"


class UserCredential(Base):
    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    credential_type: Mapped[CredentialType] = mapped_column(SQLEnum(CredentialType))
    credential_value: Mapped[str] = mapped_column(String(500))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="credentials")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[AuditEventType] = mapped_column(SQLEnum(AuditEventType))
    details: Mapped[str] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User" | None] = relationship(back_populates="audit_logs")


class SecurityPolicy(Base):
    __tablename__ = "security_policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserPermission(Base):
    __tablename__ = "user_permissions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    resource: Mapped[str] = mapped_column(String(255))
    scope: Mapped[PermissionScope] = mapped_column(SQLEnum(PermissionScope))

class EnterpriseTenant(Base):
    __tablename__ = "enterprise_tenants"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

class EnterpriseRole(Base):
    __tablename__ = "enterprise_roles"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("enterprise_tenants.id"))
    name: Mapped[str] = mapped_column(String(100))

class EnterprisePermission(Base):
    __tablename__ = "enterprise_permissions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("enterprise_roles.id"))
    permission_name: Mapped[str] = mapped_column(String(255))

class SSOConfiguration(Base):
    __tablename__ = "sso_configurations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("enterprise_tenants.id"))
    provider: Mapped[str] = mapped_column(String(50))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)

class AccessSession(Base):
    __tablename__ = "access_sessions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(512), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]

class ABACPolicy(Base):
    __tablename__ = "abac_policies"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    policy_rules: Mapped[dict[str, Any]] = mapped_column(JSON)
