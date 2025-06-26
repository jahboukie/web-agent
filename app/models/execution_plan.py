# === FORCE UPDATE ===
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .interactive_element import InteractiveElement
    from .task import Task
    from .user import User


class PlanStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    VALIDATED = "validated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    WAIT = "wait"
    SCROLL = "scroll"
    SUBMIT = "submit"
    EXTRACT = "extract"
    VERIFY = "verify"
    SCREENSHOT = "screenshot"
    HOVER = "hover"
    KEY_PRESS = "key_press"
    DRAG_DROP = "drag_drop"


class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    BLOCKED = "blocked"


class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_goal: Mapped[str] = mapped_column(Text)
    source_webpage_url: Mapped[str] = mapped_column(String(2048))
    source_webpage_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    plan_version: Mapped[int] = mapped_column(default=1)
    total_actions: Mapped[int] = mapped_column(default=0)
    estimated_duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    complexity_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    risk_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    llm_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_iterations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planning_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planning_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planning_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    automation_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requires_sensitive_actions: Mapped[bool | None] = mapped_column(
        Boolean, default=False
    )
    complexity_level: Mapped[str | None] = mapped_column(String(50), default="medium")
    plan_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_passed: Mapped[bool | None] = mapped_column(Boolean, default=False)
    validation_warnings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    validation_errors: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    requires_approval: Mapped[bool | None] = mapped_column(Boolean, default=True)
    approved_by_user: Mapped[bool | None] = mapped_column(Boolean, default=False)
    approval_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[PlanStatus] = mapped_column(
        SQLEnum(PlanStatus), default=PlanStatus.DRAFT, index=True
    )
    target_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starting_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    planning_context: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    success_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    execution_success_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    similar_plans_referenced: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    learning_tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    user_satisfaction_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fallback_plans: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    error_recovery_strategy: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    task: Mapped[Task] = relationship(back_populates="execution_plans")
    user: Mapped[User] = relationship()
    atomic_actions: Mapped[list[AtomicAction]] = relationship(
        back_populates="execution_plan",
        cascade="all, delete-orphan",
        order_by="AtomicAction.step_number",
    )


class AtomicAction(Base):
    __tablename__ = "atomic_actions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    execution_plan_id: Mapped[int] = mapped_column(
        ForeignKey("execution_plans.id"), index=True
    )
    target_element_id: Mapped[int | None] = mapped_column(
        ForeignKey("interactive_elements.id"), nullable=True
    )
    step_number: Mapped[int] = mapped_column(Integer)
    step_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(500))
    action_type: Mapped[ActionType] = mapped_column(SQLEnum(ActionType), index=True)
    target_selector: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    input_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    element_xpath: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    element_css_selector: Mapped[str | None] = mapped_column(String(500), nullable=True)
    element_attributes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    element_text_content: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    expected_outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    validation_criteria: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    preconditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    required_page_elements: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    required_page_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    fallback_actions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, default=30)
    max_retries: Mapped[int | None] = mapped_column(Integer, default=3)
    retry_delay_seconds: Mapped[int | None] = mapped_column(Integer, default=2)
    depends_on_steps: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    conditional_logic: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    skip_if_conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    is_critical: Mapped[bool | None] = mapped_column(Boolean, default=False)
    requires_confirmation: Mapped[bool | None] = mapped_column(Boolean, default=False)
    wait_condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[StepStatus] = mapped_column(
        SQLEnum(StepStatus), default=StepStatus.PENDING, index=True
    )
    executed: Mapped[bool | None] = mapped_column(Boolean, default=False)
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, default=0)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    actual_outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    validation_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    before_screenshot_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    after_screenshot_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    execution_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    performance_metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    execution_plan: Mapped[ExecutionPlan] = relationship(
        back_populates="atomic_actions"
    )
    target_element: Mapped[InteractiveElement | None] = relationship(
        back_populates="actions_taken"
    )


class PlanTemplate(Base):
    __tablename__ = "plan_templates"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100))
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    template_steps: Mapped[dict[str, Any]] = mapped_column(JSON)
    required_elements: Mapped[dict[str, Any]] = mapped_column(JSON)
    variable_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    usage_count: Mapped[int | None] = mapped_column(default=0)
    success_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_from_plans: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    website_patterns: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
