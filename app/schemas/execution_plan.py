from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator

from app.models.execution_plan import ActionType, PlanStatus


class AtomicActionBase(BaseModel):
    step_number: int = Field(ge=1)
    action_type: ActionType
    description: str = Field(max_length=500)
    target_selector: str | None = Field(None, max_length=1000)
    input_value: str | None = None
    wait_condition: str | None = Field(None, max_length=200)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    is_critical: bool = False
    requires_confirmation: bool = False
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class AtomicActionCreate(AtomicActionBase):
    execution_plan_id: int | None = None
    target_element_id: int | None = None


class AtomicActionUpdate(BaseModel):
    executed: bool | None = None
    success: bool | None = None
    error_message: str | None = None
    retry_count: int | None = None
    execution_duration_ms: int | None = None
    before_screenshot_path: str | None = None
    after_screenshot_path: str | None = None
    expected_outcome: dict[str, Any] | None = None
    actual_outcome: dict[str, Any] | None = None
    validation_passed: bool | None = None


class AtomicAction(AtomicActionBase):
    id: int
    execution_plan_id: int
    target_element_id: int | None = None
    executed: bool = False
    executed_at: datetime | None = None
    success: bool | None = None
    error_message: str | None = None
    retry_count: int = 0
    execution_duration_ms: int | None = None
    before_screenshot_path: str | None = None
    after_screenshot_path: str | None = None
    expected_outcome: dict[str, Any] = {}
    actual_outcome: dict[str, Any] = {}
    validation_passed: bool | None = None

    class Config:
        from_attributes = True


class ExecutionPlanBase(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None
    original_goal: str
    target_domain: str | None = Field(None, max_length=255)
    starting_url: str | None = Field(None, max_length=2048)
    estimated_duration_seconds: int | None = Field(None, ge=1)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    complexity_score: float = Field(ge=0.0, le=1.0, default=0.0)


class ExecutionPlanCreate(ExecutionPlanBase):
    planning_context: dict[str, Any] = {}
    atomic_actions: list[AtomicActionCreate] = []


class ExecutionPlanUpdate(BaseModel):
    status: PlanStatus | None = None
    total_actions: int | None = None
    success_probability: float | None = Field(None, ge=0.0, le=1.0)
    actual_success: bool | None = None
    validated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ExecutionPlan(ExecutionPlanBase):
    id: int
    status: PlanStatus = PlanStatus.DRAFT
    total_actions: int = 0
    planning_context: dict[str, Any] = {}
    created_at: datetime
    validated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    success_probability: float | None = None
    actual_success: bool | None = None
    fallback_plans: list[int] = []
    error_recovery_strategy: str | None = None

    # Relationships
    atomic_actions: list[AtomicAction] = []

    class Config:
        from_attributes = True

    @validator("atomic_actions")
    def validate_step_numbers(cls, v):
        if v:
            step_numbers = [action.step_number for action in v]
            if len(set(step_numbers)) != len(step_numbers):
                raise ValueError("Step numbers must be unique")
            if step_numbers and (
                min(step_numbers) < 1 or max(step_numbers) != len(step_numbers)
            ):
                raise ValueError("Step numbers must be sequential starting from 1")
        return v


class ExecutionPlanRequest(BaseModel):
    goal: str = Field(min_length=10, max_length=1000)
    target_url: str | None = Field(None, max_length=2048)
    user_context: dict[str, Any] = {}
    max_actions: int = Field(default=20, ge=1, le=100)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    allow_sensitive_actions: bool = False
    require_confirmation_for_critical: bool = True


class ExecutionPlanResponse(BaseModel):
    execution_plan: ExecutionPlan
    planning_time_ms: int
    confidence_analysis: dict[str, Any] = {}
    identified_risks: list[str] = []
    alternative_approaches: list[str] = []
    estimated_success_rate: float = Field(ge=0.0, le=1.0)


class PlanValidationRequest(BaseModel):
    execution_plan_id: int
    validate_elements: bool = True
    check_permissions: bool = True
    estimate_success_rate: bool = True


class PlanValidationResponse(BaseModel):
    is_valid: bool
    validation_score: float = Field(ge=0.0, le=1.0)
    issues_found: list[dict[str, Any]] = []
    recommendations: list[str] = []
    estimated_duration_seconds: int | None = None
    risk_assessment: dict[str, Any] = {}
