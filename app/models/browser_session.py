# === FORCE UPDATE ===
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .task import Task
    from .task_execution import TaskExecution
    from .user import User
    from .web_page import WebPage


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

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    current_page_id: Mapped[int | None] = mapped_column(ForeignKey("web_pages.id"), nullable=True)

    session_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    browser_type: Mapped[BrowserType] = mapped_column(SQLEnum(BrowserType))
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus), default=SessionStatus.INITIALIZING)

    headless: Mapped[bool | None] = mapped_column(Boolean, default=True)
    user_agent: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    viewport_width: Mapped[int | None] = mapped_column(Integer, default=1920)
    viewport_height: Mapped[int | None] = mapped_column(Integer, default=1080)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)

    current_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    page_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cookies: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    local_storage: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    session_storage: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    memory_usage_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_usage_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    network_requests_count: Mapped[int | None] = mapped_column(Integer, default=0)
    total_data_transferred_kb: Mapped[int | None] = mapped_column(Integer, default=0)

    error_count: Mapped[int | None] = mapped_column(Integer, default=0)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    cloud_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cloud_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cloud_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)

    fingerprint_randomization: Mapped[bool | None] = mapped_column(Boolean, default=True)
    proxy_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stealth_mode: Mapped[bool | None] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="browser_sessions")
    task: Mapped["Task" | None] = relationship(back_populates="browser_sessions") # type: ignore
    current_page: Mapped["WebPage" | None] = relationship(back_populates="browser_sessions") # type: ignore
    executions: Mapped[list["TaskExecution"]] = relationship(back_populates="browser_session")
