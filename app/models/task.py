from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


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

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Task definition
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    goal = Column(Text, nullable=False)  # Natural language goal
    target_url = Column(String(2048), nullable=True)  # Initial URL if specified

    # Task execution metadata
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(
        SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False
    )
    progress_percentage = Column(Integer, default=0)

    # Execution data
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)

    # Phase 2C: AI Planning Integration
    user_goal = Column(
        Text, nullable=True
    )  # Store user's natural language goal for planning
    planning_status = Column(
        String(50), nullable=True
    )  # Status of plan generation process
    requires_approval = Column(
        Boolean, default=True
    )  # Whether generated plans need approval

    # Results and errors
    result_data = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, default=dict)

    # Background processing fields (Phase 2B Enhancement)
    background_task_id = Column(String(255), nullable=True, index=True)
    queue_name = Column(String(100), default="default", nullable=False)
    worker_id = Column(String(255), nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Progress tracking
    progress_details = Column(
        JSON, default=dict
    )  # {"current_step": "extracting_elements", "progress": 45}
    estimated_completion_at = Column(DateTime(timezone=True), nullable=True)

    # Resource tracking
    memory_usage_mb = Column(Integer, nullable=True)
    browser_session_id = Column(String(255), nullable=True)

    # Enhanced error tracking
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    # Timing
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_duration_seconds = Column(Integer, nullable=True)
    actual_duration_seconds = Column(Integer, nullable=True)

    # Configuration
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=300)  # 5 minutes default

    # User preferences for this task
    require_confirmation = Column(Boolean, default=False)
    allow_sensitive_actions = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="tasks")
    execution_plans = relationship(
        "ExecutionPlan", back_populates="task", cascade="all, delete-orphan"
    )
    executions = relationship(
        "TaskExecution", back_populates="task", cascade="all, delete-orphan"
    )
    browser_sessions = relationship("BrowserSession", back_populates="task")
