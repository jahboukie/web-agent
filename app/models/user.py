# === FORCE UPDATE ===
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from sqlalchemy import JSON
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .browser_session import BrowserSession
    from .security import AuditLog
    from .security import UserCredential
    from .task import Task


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    api_rate_limit: Mapped[int | None] = mapped_column(Integer, default=100)
    employee_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sso_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sso_user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    sso_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    backup_codes: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    trust_score: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    risk_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    data_classification: Mapped[str | None] = mapped_column(
        String(50), default="internal"
    )
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    gdpr_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    tasks: Mapped[list[Task]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    credentials: Mapped[list[UserCredential]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")
    browser_sessions: Mapped[list[BrowserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
