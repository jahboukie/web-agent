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
    from .browser_session import BrowserSession
    from .task import Task
    from .web_page import WebPage


class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExecutionTrigger(str, Enum):
    USER_REQUEST = "user_request"
    SCHEDULED = "scheduled"
    RETRY = "retry"
    WEBHOOK = "webhook"
    API_CALL = "api_call"


class TaskExecution(Base):
    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    browser_session_id: Mapped[int | None] = mapped_column(ForeignKey("browser_sessions.id"), nullable=True)

    execution_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[ExecutionStatus] = mapped_column(SQLEnum(ExecutionStatus), default=ExecutionStatus.QUEUED)
    trigger: Mapped[ExecutionTrigger] = mapped_column(SQLEnum(ExecutionTrigger))
    
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    current_step: Mapped[int | None] = mapped_column(Integer, default=0)
    total_steps: Mapped[int | None] = mapped_column(Integer, default=0)
    progress_percentage: Mapped[int | None] = mapped_column(Integer, default=0)
    current_action_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    screenshots: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    retry_attempt: Mapped[int | None] = mapped_column(Integer, default=0)
    max_retries: Mapped[int | None] = mapped_column(Integer, default=3)
    retry_delay_seconds: Mapped[int | None] = mapped_column(Integer, default=60)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    actions_executed: Mapped[int | None] = mapped_column(Integer, default=0)
    pages_visited: Mapped[int | None] = mapped_column(Integer, default=0)
    elements_interacted: Mapped[int | None] = mapped_column(Integer, default=0)
    data_extracted_kb: Mapped[int | None] = mapped_column(Integer, default=0)
    
    plan_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_satisfaction_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    cpu_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_peak_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    network_requests_count: Mapped[int | None] = mapped_column(Integer, default=0)
    data_transferred_kb: Mapped[int | None] = mapped_column(Integer, default=0)
    
    user_confirmations_required: Mapped[int | None] = mapped_column(Integer, default=0)
    user_confirmations_received: Mapped[int | None] = mapped_column(Integer, default=0)
    sensitive_actions_count: Mapped[int | None] = mapped_column(Integer, default=0)
    compliance_checks_passed: Mapped[int | None] = mapped_column(Integer, default=0)

    task: Mapped["Task"] = relationship(back_populates="executions")
    browser_session: Mapped["BrowserSession" | None] = relationship(back_populates="executions")

class ContentBlock(Base):
    __tablename__ = "content_blocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    web_page_id: Mapped[int] = mapped_column(ForeignKey("web_pages.id"))
    block_type: Mapped[str] = mapped_column(String(50))
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    dom_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    nesting_level: Mapped[int | None] = mapped_column(default=0)
    sibling_index: Mapped[int | None] = mapped_column(default=0)
    x_coordinate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    y_coordinate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_visible: Mapped[bool | None] = mapped_column(default=True)
    semantic_importance: Mapped[float | None] = mapped_column(default=0.0)
    semantic_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    discovered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    web_page: Mapped["WebPage"] = relationship(back_populates="content_blocks")

class ActionCapability(Base):
    __tablename__ = "action_capabilities"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    web_page_id: Mapped[int] = mapped_column(ForeignKey("web_pages.id"))
    action_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    required_elements: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    required_data: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    prerequisites: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    feasibility_score: Mapped[float | None] = mapped_column(default=0.0)
    complexity_score: Mapped[float | None] = mapped_column(default=0.0)
    confidence_score: Mapped[float | None] = mapped_column(default=0.0)
    attempted_count: Mapped[int | None] = mapped_column(default=0)
    success_count: Mapped[int | None] = mapped_column(default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    analysis_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    web_page: Mapped["WebPage"] = relationship(back_populates="action_capabilities")
