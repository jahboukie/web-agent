from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    current_page_id = Column(Integer, ForeignKey("web_pages.id"), nullable=True)

    # Session identification
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    browser_type = Column(SQLEnum(BrowserType), nullable=False)
    status = Column(
        SQLEnum(SessionStatus), default=SessionStatus.INITIALIZING, nullable=False
    )

    # Browser configuration
    headless = Column(Boolean, default=True)
    user_agent = Column(String(1000), nullable=True)
    viewport_width = Column(Integer, default=1920)
    viewport_height = Column(Integer, default=1080)
    timezone = Column(String(100), nullable=True)
    locale = Column(String(10), nullable=True)

    # Session context
    current_url = Column(String(2048), nullable=True)
    page_title = Column(String(512), nullable=True)
    cookies = Column(JSON, default=list)
    local_storage = Column(JSON, default=dict)
    session_storage = Column(JSON, default=dict)

    # Performance tracking
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_activity_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    terminated_at = Column(DateTime(timezone=True), nullable=True)

    # Resource usage
    memory_usage_mb = Column(Integer, nullable=True)
    cpu_usage_percent = Column(Integer, nullable=True)
    network_requests_count = Column(Integer, default=0)
    total_data_transferred_kb = Column(Integer, default=0)

    # Error tracking
    error_count = Column(Integer, default=0)
    last_error_message = Column(Text, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    # Cloud browser integration
    cloud_provider = Column(String(100), nullable=True)  # e.g., "browserbase"
    cloud_session_id = Column(String(255), nullable=True)
    cloud_endpoint = Column(String(500), nullable=True)

    # Anti-detection measures
    fingerprint_randomization = Column(Boolean, default=True)
    proxy_used = Column(String(255), nullable=True)
    stealth_mode = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="browser_sessions")
    task = relationship("Task", back_populates="browser_sessions")
    current_page = relationship("WebPage", back_populates="browser_sessions")
    executions = relationship("TaskExecution", back_populates="browser_session")
