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
    from app.models.browser_session import BrowserSession
    from app.models.execution_plan import ExecutionPlan
    from app.models.task_execution import TaskExecution
    from app.models.user import User


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Task definition
    title: Mapped[str] = Column(String(255), nullable=False)
    description: Mapped[str] = Column(Text, nullable=False)
    goal: Mapped[str] = Column(Text, nullable=False)
    target_url: Mapped[str | None] = Column(String(2048), nullable=True)

    # Task execution metadata
    status: Mapped[TaskStatus] = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority: Mapped[TaskPriority] = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    progress_percentage: Mapped[int] = Column(Integer, default=0)

    # Execution data
    current_step: Mapped[int] = Column(Integer, default=0)
    total_steps: Mapped[int] = Column(Integer, default=0)

    # Phase 2C: AI Planning Integration
    user_goal: Mapped[str | None] = Column(Text, nullable=True)
    planning_status: Mapped[str | None] = Column(String(50), nullable=True)
    requires_approval: Mapped[bool] = Column(Boolean, default=True)

    # Results and errors
    result_data: Mapped[dict[str, Any]] = Column(JSON, default=dict)
    error_message: Mapped[str | None] = Column(Text, nullable=True)
    error_details: Mapped[dict[str, Any]] = Column(JSON, default=dict)

    # Background processing fields
    background_task_id: Mapped[str | None] = Column(String(255), nullable=True, index=True)
    queue_name: Mapped[str] = Column(String(100), default="default", nullable=False)
    worker_id: Mapped[str | None] = Column(String(255), nullable=True)
    processing_started_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)

    # Progress tracking
    progress_details: Mapped[dict[str, Any]] = Column(JSON, default=dict)
    estimated_completion_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)

    # Resource tracking
    memory_usage_mb: Mapped[int | None] = Column(Integer, nullable=True)
    browser_session_id: Mapped[str | None] = Column(String(255), nullable=True)

    # Enhanced error tracking
    last_error_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)

    # Timing
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    started_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
    estimated_duration_seconds: Mapped[int | None] = Column(Integer, nullable=True)
    actual_duration_seconds: Mapped[int | None] = Column(Integer, nullable=True)

    # Configuration
    max_retries: Mapped[int] = Column(Integer, default=3)
    retry_count: Mapped[int] = Column(Integer, default=0)
    timeout_seconds: Mapped[int] = Column(Integer, default=300)

    # User preferences for this task
    require_confirmation: Mapped[bool] = Column(Boolean, default=False)
    allow_sensitive_actions: Mapped[bool] = Column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    execution_plans: Mapped[list["ExecutionPlan"]] = relationship("ExecutionPlan", back_populates="task", cascade="all, delete-orphan")
    executions: Mapped[list["TaskExecution"]] = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    browser_sessions: Mapped[list["BrowserSession"]] = relationship("BrowserSession", back_populates="task")
