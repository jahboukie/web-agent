from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.task_execution import TaskExecution
    from app.models.user import User
    from app.models.web_page import WebPage


class SessionStatus(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    ERROR = "error"


class BrowserType(str, Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    CHROME = "chrome"
    EDGE = "edge"


class BrowserSession(Base):
    __tablename__ = "browser_sessions"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int | None] = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    current_page_id: Mapped[int | None] = Column(Integer, ForeignKey("web_pages.id"), nullable=True)

    # Session identification
    session_id: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    browser_type: Mapped[BrowserType] = Column(SQLEnum(BrowserType), nullable=False)
    status: Mapped[SessionStatus] = Column(SQLEnum(SessionStatus), default=SessionStatus.INITIALIZING, nullable=False)

    # Browser configuration
    headless: Mapped[bool] = Column(Boolean, default=True)
    user_agent: Mapped[str | None] = Column(String(1000), nullable=True)
    viewport_width: Mapped[int] = Column(Integer, default=1920)
    viewport_height: Mapped[int] = Column(Integer, default=1080)
    timezone: Mapped[str | None] = Column(String(100), nullable=True)
    locale: Mapped[str | None] = Column(String(10), nullable=True)

    # Session context
    current_url: Mapped[str | None] = Column(String(2048), nullable=True)
    page_title: Mapped[str | None] = Column(String(512), nullable=True)
    cookies: Mapped[list[Any]] = Column(JSON, default=list)
    local_storage: Mapped[dict[str, Any]] = Column(JSON, default=dict)
    session_storage: Mapped[dict[str, Any]] = Column(JSON, default=dict)

    # Performance tracking
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    terminated_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)

    # Resource usage
    memory_usage_mb: Mapped[int | None] = Column(Integer, nullable=True)
    cpu_usage_percent: Mapped[int | None] = Column(Integer, nullable=True)
    network_requests_count: Mapped[int] = Column(Integer, default=0)
    total_data_transferred_kb: Mapped[int] = Column(Integer, default=0)

    # Error tracking
    error_count: Mapped[int] = Column(Integer, default=0)
    last_error_message: Mapped[str | None] = Column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)

    # Cloud browser integration
    cloud_provider: Mapped[str | None] = Column(String(100), nullable=True)
    cloud_session_id: Mapped[str | None] = Column(String(255), nullable=True)
    cloud_endpoint: Mapped[str | None] = Column(String(500), nullable=True)

    # Anti-detection measures
    fingerprint_randomization: Mapped[bool] = Column(Boolean, default=True)
    proxy_used: Mapped[str | None] = Column(String(255), nullable=True)
    stealth_mode: Mapped[bool] = Column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="browser_sessions")
    task: Mapped["Task" | None] = relationship("Task", back_populates="browser_sessions")
    current_page: Mapped["WebPage" | None] = relationship("WebPage", back_populates="browser_sessions")
    executions: Mapped[list["TaskExecution"]] = relationship("TaskExecution", back_populates="browser_session")
