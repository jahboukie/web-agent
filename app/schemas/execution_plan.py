from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from app.models.execution_plan import PlanStatus, ActionType


class AtomicActionBase(BaseModel):
    step_number: int = Field(ge=1)
    action_type: ActionType
    description: str = Field(max_length=500)
    target_selector: Optional[str] = Field(None, max_length=1000)
    input_value: Optional[str] = None
    wait_condition: Optional[str] = Field(None, max_length=200)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    is_critical: bool = False
    requires_confirmation: bool = False
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class AtomicActionCreate(AtomicActionBase):
    execution_plan_id: Optional[int] = None
    target_element_id: Optional[int] = None


class AtomicActionUpdate(BaseModel):
    executed: Optional[bool] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    execution_duration_ms: Optional[int] = None
    before_screenshot_path: Optional[str] = None
    after_screenshot_path: Optional[str] = None
    expected_outcome: Optional[Dict[str, Any]] = None
    actual_outcome: Optional[Dict[str, Any]] = None
    validation_passed: Optional[bool] = None


class AtomicAction(AtomicActionBase):
    id: int
    execution_plan_id: int
    target_element_id: Optional[int] = None
    executed: bool = False
    executed_at: Optional[datetime] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    execution_duration_ms: Optional[int] = None
    before_screenshot_path: Optional[str] = None
    after_screenshot_path: Optional[str] = None
    expected_outcome: Dict[str, Any] = {}
    actual_outcome: Dict[str, Any] = {}
    validation_passed: Optional[bool] = None

    class Config:
        from_attributes = True


class ExecutionPlanBase(BaseModel):
    title: str = Field(max_length=255)
    description: Optional[str] = None
    original_goal: str
    target_domain: Optional[str] = Field(None, max_length=255)
    starting_url: Optional[str] = Field(None, max_length=2048)
    estimated_duration_seconds: Optional[int] = Field(None, ge=1)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    complexity_score: float = Field(ge=0.0, le=1.0, default=0.0)


class ExecutionPlanCreate(ExecutionPlanBase):
    planning_context: Dict[str, Any] = {}
    atomic_actions: List[AtomicActionCreate] = []


class ExecutionPlanUpdate(BaseModel):
    status: Optional[PlanStatus] = None
    total_actions: Optional[int] = None
    success_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    actual_success: Optional[bool] = None
    validated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExecutionPlan(ExecutionPlanBase):
    id: int
    status: PlanStatus = PlanStatus.DRAFT
    total_actions: int = 0
    planning_context: Dict[str, Any] = {}
    created_at: datetime
    validated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    success_probability: Optional[float] = None
    actual_success: Optional[bool] = None
    fallback_plans: List[int] = []
    error_recovery_strategy: Optional[str] = None
    
    # Relationships
    atomic_actions: List[AtomicAction] = []

    class Config:
        from_attributes = True

    @validator('atomic_actions')
    def validate_step_numbers(cls, v):
        if v:
            step_numbers = [action.step_number for action in v]
            if len(set(step_numbers)) != len(step_numbers):
                raise ValueError("Step numbers must be unique")
            if step_numbers and (min(step_numbers) < 1 or max(step_numbers) != len(step_numbers)):
                raise ValueError("Step numbers must be sequential starting from 1")
        return v


class ExecutionPlanRequest(BaseModel):
    goal: str = Field(min_length=10, max_length=1000)
    target_url: Optional[str] = Field(None, max_length=2048)
    user_context: Dict[str, Any] = {}
    max_actions: int = Field(default=20, ge=1, le=100)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    allow_sensitive_actions: bool = False
    require_confirmation_for_critical: bool = True


class ExecutionPlanResponse(BaseModel):
    execution_plan: ExecutionPlan
    planning_time_ms: int
    confidence_analysis: Dict[str, Any] = {}
    identified_risks: List[str] = []
    alternative_approaches: List[str] = []
    estimated_success_rate: float = Field(ge=0.0, le=1.0)


class PlanValidationRequest(BaseModel):
    execution_plan_id: int
    validate_elements: bool = True
    check_permissions: bool = True
    estimate_success_rate: bool = True


class PlanValidationResponse(BaseModel):
    is_valid: bool
    validation_score: float = Field(ge=0.0, le=1.0)
    issues_found: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    estimated_duration_seconds: Optional[int] = None
    risk_assessment: Dict[str, Any] = {}