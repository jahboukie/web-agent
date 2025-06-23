from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator

from app.models.execution_plan import ActionType, PlanStatus, StepStatus


class PlanningOptions(BaseModel):
    """Options for controlling AI plan generation."""

    confidence_threshold: float = Field(
        0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence required for auto-approval",
    )
    risk_tolerance: str = Field(
        "medium", description="Risk tolerance level: low, medium, high"
    )
    planning_timeout_seconds: int = Field(
        300, ge=30, le=600, description="Maximum time to spend planning"
    )
    include_screenshots: bool = Field(
        True, description="Whether to include screenshots in plan steps"
    )
    require_user_approval: bool = Field(
        True, description="Whether to require explicit user approval"
    )
    allow_sensitive_actions: bool = Field(
        False, description="Whether to allow file uploads, payments, etc."
    )
    planning_temperature: float = Field(
        0.1, ge=0.0, le=1.0, description="LLM temperature for planning"
    )
    max_agent_iterations: int = Field(
        15, ge=5, le=30, description="Maximum ReAct agent iterations"
    )


class PlanGenerationRequest(BaseModel):
    """Request to generate an AI execution plan."""

    task_id: int = Field(..., description="ID of completed webpage parsing task")
    user_goal: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Natural language description of what to accomplish",
    )
    planning_options: PlanningOptions | None = Field(default_factory=PlanningOptions)
    context_hints: dict[str, Any] | None = Field(
        None, description="Additional context to help with planning"
    )


class ActionStepSchema(BaseModel):
    """Schema for individual action steps in execution plan."""

    step_number: int = Field(..., ge=1, description="Order within the plan")
    step_name: str = Field(
        ..., min_length=5, max_length=200, description="Human-readable step name"
    )
    description: str = Field(
        ..., min_length=10, max_length=500, description="Detailed step description"
    )
    action_type: ActionType = Field(..., description="Type of action to perform")

    # Element targeting
    element_selector: str | None = Field(
        None, max_length=500, description="CSS selector for target element"
    )
    element_xpath: str | None = Field(
        None, max_length=1000, description="XPath for target element"
    )
    element_text_content: str | None = Field(
        None, max_length=500, description="Expected element text"
    )
    element_attributes: dict[str, Any] | None = Field(
        None, description="Expected element attributes"
    )

    # Action data
    input_value: str | None = Field(None, description="Text to type or value to input")
    action_data: dict[str, Any] | None = Field(
        None, description="Additional action parameters"
    )

    # Confidence and validation
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in this step"
    )
    expected_outcome: str | None = Field(
        None, description="What should happen after this step"
    )
    validation_criteria: dict[str, Any] | None = Field(
        None, description="How to verify step succeeded"
    )

    # Error handling
    fallback_actions: list[dict[str, Any]] | None = Field(
        None, description="Alternative actions if primary fails"
    )
    timeout_seconds: int = Field(30, ge=5, le=300, description="Timeout for this step")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")

    # Dependencies
    depends_on_steps: list[int] | None = Field(
        None, description="Step numbers this depends on"
    )
    conditional_logic: dict[str, Any] | None = Field(
        None, description="Conditional execution rules"
    )

    # Metadata
    is_critical: bool = Field(
        False, description="Whether failure should abort entire plan"
    )
    requires_confirmation: bool = Field(
        False, description="Whether to ask user before executing"
    )

    status: StepStatus | None = Field(
        StepStatus.PENDING, description="Current execution status"
    )


class ExecutionPlanSchema(BaseModel):
    """Schema for AI-generated execution plan."""

    id: int | None = Field(None, description="Plan ID (set after creation)")
    task_id: int = Field(..., description="Source parsing task ID")
    user_id: int = Field(..., description="User who requested the plan")

    # Plan metadata
    title: str = Field(..., min_length=10, max_length=255, description="Plan title")
    description: str | None = Field(None, description="Plan description")
    original_goal: str = Field(..., description="User's original goal")
    source_webpage_url: str = Field(..., description="URL that was analyzed")
    plan_version: int = Field(1, ge=1, description="Plan version number")

    # Plan content
    total_actions: int = Field(..., ge=1, description="Total number of action steps")
    estimated_duration_seconds: int = Field(
        ..., ge=1, description="Estimated execution time"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall plan confidence"
    )
    complexity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Plan complexity rating"
    )

    # Classification
    automation_category: str | None = Field(None, description="Category of automation")
    requires_sensitive_actions: bool = Field(
        False, description="Whether plan includes sensitive actions"
    )
    complexity_level: str = Field(
        "medium", description="simple, medium, complex, expert"
    )

    # AI metadata
    llm_model_used: str | None = Field(
        None, description="LLM model used for generation"
    )
    agent_iterations: int | None = Field(
        None, description="Number of agent reasoning steps"
    )
    planning_tokens_used: int | None = Field(
        None, description="Tokens consumed during planning"
    )
    planning_duration_ms: int | None = Field(
        None, description="Time spent generating plan"
    )

    # Quality metrics
    plan_quality_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Post-generation quality score"
    )
    validation_passed: bool = Field(False, description="Whether plan passed validation")
    validation_warnings: list[str] | None = Field(
        None, description="Non-blocking validation issues"
    )
    validation_errors: list[str] | None = Field(
        None, description="Blocking validation issues"
    )

    # Approval workflow
    requires_approval: bool = Field(
        True, description="Whether plan needs human approval"
    )
    approved_by_user: bool = Field(False, description="Whether user has approved")
    approval_feedback: str | None = Field(None, description="User feedback on plan")

    # Risk assessment
    risk_assessment: dict[str, Any] | None = Field(
        None, description="Risk factors and mitigation"
    )

    # Learning
    similar_plans_referenced: list[int] | None = Field(
        None, description="Similar successful plan IDs"
    )
    learning_tags: list[str] | None = Field(None, description="Tags for categorization")

    # Status and timestamps
    status: PlanStatus = Field(PlanStatus.DRAFT, description="Current plan status")
    created_at: datetime | None = Field(None, description="Plan creation time")
    approved_at: datetime | None = Field(None, description="Plan approval time")

    # Action steps
    action_steps: list[ActionStepSchema] = Field([], description="List of action steps")

    class Config:
        from_attributes = True


class PlanGenerationResponse(BaseModel):
    """Response from plan generation endpoint."""

    plan_id: int = Field(..., description="Generated plan ID")
    status: str = Field(..., description="Generation status")
    message: str = Field(..., description="Status message")
    estimated_completion_seconds: int = Field(
        ..., description="Estimated time to complete generation"
    )
    check_status_url: str = Field(..., description="URL to check generation progress")


class PlanStatusResponse(BaseModel):
    """Response for plan status check."""

    plan_id: int = Field(..., description="Plan ID")
    status: PlanStatus = Field(..., description="Current plan status")
    progress_percentage: int = Field(
        ..., ge=0, le=100, description="Generation progress"
    )
    current_step: str = Field(..., description="Current generation step")
    message: str = Field(..., description="Status message")

    # Plan summary (when available)
    total_steps: int | None = Field(None, description="Number of action steps")
    overall_confidence: float | None = Field(
        None, description="Overall confidence score"
    )
    complexity_level: str | None = Field(None, description="Plan complexity")
    requires_approval: bool | None = Field(
        None, description="Whether approval is needed"
    )

    # Generation metadata
    generation_duration_ms: int | None = Field(
        None, description="Time spent generating"
    )
    agent_iterations: int | None = Field(None, description="Agent reasoning steps")
    tokens_used: int | None = Field(None, description="LLM tokens consumed")


class PlanApprovalRequest(BaseModel):
    """Request to approve or reject a plan."""

    approval_decision: str = Field(..., description="approve, reject, or modify")
    feedback: str | None = Field(None, max_length=1000, description="User feedback")
    modifications: list[dict[str, Any]] | None = Field(
        None, description="Requested modifications"
    )
    confidence_override: float | None = Field(
        None, ge=0.0, le=1.0, description="Override confidence score"
    )

    @validator("approval_decision")
    def validate_decision(cls, v):
        if v not in ["approve", "reject", "modify"]:
            raise ValueError("approval_decision must be approve, reject, or modify")
        return v


class PlanApprovalResponse(BaseModel):
    """Response from plan approval endpoint."""

    plan_id: int = Field(..., description="Plan ID")
    status: PlanStatus = Field(..., description="Updated plan status")
    ready_for_execution: bool = Field(
        ..., description="Whether plan is ready for execution"
    )
    message: str = Field(..., description="Status message")
    next_action_url: str | None = Field(
        None, description="URL for next action (if applicable)"
    )


class PlanValidationResult(BaseModel):
    """Result of plan validation."""

    is_valid: bool = Field(..., description="Whether plan passed validation")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Validation confidence"
    )
    warnings: list[str] = Field([], description="Non-blocking validation warnings")
    errors: list[str] = Field([], description="Blocking validation errors")

    # Detailed validation results
    element_validation: dict[str, bool] = Field(
        {}, description="Element selector validation results"
    )
    sequence_validation: dict[str, bool] = Field(
        {}, description="Action sequence validation results"
    )
    safety_validation: dict[str, bool] = Field(
        {}, description="Safety constraint validation results"
    )

    recommendations: list[str] = Field([], description="Improvement recommendations")


class PlanMetrics(BaseModel):
    """Metrics and analytics for plan generation."""

    total_plans_generated: int = Field(..., description="Total plans generated")
    average_confidence: float = Field(..., description="Average plan confidence")
    success_rate: float = Field(..., description="Plan success rate")
    average_generation_time_ms: int = Field(..., description="Average generation time")

    # Category breakdown
    category_distribution: dict[str, int] = Field({}, description="Plans by category")
    complexity_distribution: dict[str, int] = Field(
        {}, description="Plans by complexity"
    )

    # Quality metrics
    approval_rate: float = Field(..., description="Rate of plan approval")
    user_satisfaction: float = Field(..., description="Average user satisfaction")

    # Performance
    average_steps_per_plan: float = Field(..., description="Average steps per plan")
    average_tokens_per_plan: int = Field(..., description="Average tokens per plan")


class PlanTemplateSchema(BaseModel):
    """Schema for reusable plan templates."""

    id: int | None = Field(None, description="Template ID")
    name: str = Field(..., min_length=5, max_length=200, description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    tags: list[str] | None = Field([], description="Search tags")

    # Template content
    template_steps: list[dict[str, Any]] = Field(
        ..., description="Step template structure"
    )
    required_elements: list[dict[str, Any]] = Field(
        ..., description="Required page elements"
    )
    variable_fields: list[dict[str, Any]] | None = Field(
        [], description="Fields requiring user input"
    )

    # Usage statistics
    usage_count: int = Field(0, description="Number of times used")
    success_rate: float | None = Field(None, description="Success rate when used")
    average_confidence: float | None = Field(
        None, description="Average confidence when used"
    )

    # Metadata
    created_at: datetime | None = Field(None, description="Template creation time")
    last_used_at: datetime | None = Field(None, description="Last usage time")

    class Config:
        from_attributes = True
