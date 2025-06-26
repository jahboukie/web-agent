from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic.fields import FieldValidationInfo  # type: ignore

from app.models.task import TaskPriority, TaskStatus
from app.schemas.execution_plan import ExecutionPlan


class TaskBase(BaseModel):
    title: str = Field(max_length=255)
    description: str
    goal: str
    target_url: HttpUrl | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    require_confirmation: bool = False
    allow_sensitive_actions: bool = False


class TaskCreate(TaskBase):
    user_id: int | None = None  # Will be set from authentication


class TaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    progress_percentage: int | None = Field(None, ge=0, le=100)
    current_step: int | None = None
    result_data: dict[str, Any] | None = None
    error_message: str | None = None
    error_details: dict[str, Any] | None = None
    require_confirmation: bool | None = None
    allow_sensitive_actions: bool | None = None


class Task(TaskBase):
    id: int
    user_id: int
    status: TaskStatus = TaskStatus.PENDING
    progress_percentage: int = 0
    execution_plan_id: int | None = None
    current_step: int = 0
    total_steps: int = 0
    result_data: dict[str, Any] = {}
    error_message: str | None = None
    error_details: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_duration_seconds: int | None = None
    actual_duration_seconds: int | None = None
    retry_count: int = 0

    # Optional relationships
    execution_plan: ExecutionPlan | None = None

    class Config:
        from_attributes = True

    @field_validator("progress_percentage")
    @classmethod
    def validate_progress(cls, v: int, info: FieldValidationInfo) -> int:
        if v < 0 or v > 100:
            raise ValueError("Progress percentage must be between 0 and 100")
        return v


class TaskExecutionRequest(BaseModel):
    task_id: int
    force_restart: bool = False
    skip_validation: bool = False
    debug_mode: bool = False
    screenshot_frequency: int = Field(
        default=5, ge=1, le=50
    )  # Screenshots every N actions


class TaskExecutionResponse(BaseModel):
    task_id: int
    execution_id: str
    status: str
    message: str
    estimated_duration_seconds: int | None = None


class TaskStatusUpdate(BaseModel):
    task_id: int
    status: TaskStatus
    progress_percentage: int = Field(ge=0, le=100)
    current_step: int
    current_action_description: str | None = None
    screenshots: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskResult(BaseModel):
    task_id: int
    success: bool
    result_data: dict[str, Any] = {}
    extracted_data: dict[str, Any] = {}
    execution_duration_seconds: int
    actions_executed: int
    pages_visited: int
    screenshots: list[str] = []
    error_message: str | None = None
    error_details: dict[str, Any] = {}
    quality_score: float | None = Field(None, ge=0.0, le=1.0)
    completion_timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskList(BaseModel):
    tasks: list[Task]
    total_count: int
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_previous: bool = False


class TaskFilters(BaseModel):
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    domain: str | None = None
    search_query: str | None = Field(None, max_length=200)


class TaskStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    pending_tasks: int
    success_rate: float = Field(ge=0.0, le=1.0)
    average_duration_seconds: float | None = None
    most_common_domains: list[dict[str, Any]] = []
    recent_activity: list[dict[str, Any]] = []
