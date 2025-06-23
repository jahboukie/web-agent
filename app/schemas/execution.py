from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExecutionRequest(BaseModel):
    """Request to start executing an approved ExecutionPlan."""

    plan_id: int = Field(description="ID of the ExecutionPlan to execute")
    execution_options: dict[str, Any] | None = Field(
        default=None, description="Optional execution configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": 123,
                "execution_options": {
                    "take_screenshots": True,
                    "screenshot_frequency": "every_step",
                    "timeout_seconds": 300,
                    "retry_failed_steps": True,
                    "max_retries": 3,
                },
            }
        }


class ExecutionResponse(BaseModel):
    """Response when execution is started."""

    execution_id: str = Field(description="Unique identifier for this execution")
    plan_id: int = Field(description="ID of the ExecutionPlan being executed")
    status: str = Field(description="Current execution status")
    message: str = Field(description="Human-readable status message")
    started_at: datetime = Field(description="When execution started")
    check_status_url: str = Field(description="URL to check execution status")
    estimated_duration_seconds: int | None = Field(
        default=None, description="Estimated time to complete execution"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_id": 123,
                "status": "executing",
                "message": "Plan execution started successfully",
                "started_at": "2025-06-20T10:30:00Z",
                "check_status_url": "/api/v1/execute/550e8400-e29b-41d4-a716-446655440000",
                "estimated_duration_seconds": 300,
            }
        }


class ExecutionStatusResponse(BaseModel):
    """Real-time execution status response."""

    execution_id: str = Field(description="Unique identifier for this execution")
    plan_id: int = Field(description="ID of the ExecutionPlan being executed")
    status: str = Field(description="Current execution status")
    started_at: str = Field(description="When execution started (ISO format)")
    completed_at: str | None = Field(
        default=None, description="When execution completed (ISO format)"
    )
    current_step: int = Field(description="Current step number being executed")
    total_steps: int = Field(description="Total number of steps in the plan")
    progress_percentage: int = Field(description="Execution progress (0-100)")
    success: bool = Field(description="Whether execution was successful")
    error_message: str | None = Field(
        default=None, description="Error message if execution failed"
    )
    executed_actions: int = Field(description="Number of actions executed so far")
    screenshots_captured: int = Field(description="Number of screenshots taken")
    execution_duration_seconds: float = Field(
        description="Total execution time in seconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_id": 123,
                "status": "executing",
                "started_at": "2025-06-20T10:30:00Z",
                "completed_at": None,
                "current_step": 3,
                "total_steps": 8,
                "progress_percentage": 37,
                "success": False,
                "error_message": None,
                "executed_actions": 3,
                "screenshots_captured": 6,
                "execution_duration_seconds": 45.2,
            }
        }


class ExecutionControlResponse(BaseModel):
    """Response for execution control actions (pause, resume, cancel)."""

    execution_id: str = Field(description="Unique identifier for this execution")
    action: str = Field(description="Control action performed")
    success: bool = Field(description="Whether the action was successful")
    message: str = Field(description="Human-readable result message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the action was performed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "action": "pause",
                "success": True,
                "message": "Execution paused successfully",
                "timestamp": "2025-06-20T10:35:00Z",
            }
        }


class ActionResult(BaseModel):
    """Result of executing a single action step."""

    step_number: int = Field(description="Step number in the execution plan")
    action_type: str = Field(description="Type of action executed")
    description: str = Field(description="Description of the action")
    success: bool = Field(description="Whether the action succeeded")
    started_at: str = Field(description="When action started (ISO format)")
    completed_at: str = Field(description="When action completed (ISO format)")
    duration_ms: int = Field(description="Action execution time in milliseconds")
    error_message: str | None = Field(
        default=None, description="Error message if action failed"
    )
    before_screenshot: str | None = Field(
        default=None, description="Screenshot path before action"
    )
    after_screenshot: str | None = Field(
        default=None, description="Screenshot path after action"
    )
    target_selector: str | None = Field(
        default=None, description="Element selector used for the action"
    )
    input_value: str | None = Field(
        default=None, description="Input value used for the action"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "step_number": 1,
                "action_type": "click",
                "description": "Click the 'Sign In' button",
                "success": True,
                "started_at": "2025-06-20T10:30:05Z",
                "completed_at": "2025-06-20T10:30:07Z",
                "duration_ms": 2150,
                "error_message": None,
                "before_screenshot": "screenshots/execution_123_step_1_before.png",
                "after_screenshot": "screenshots/execution_123_step_1_after.png",
                "target_selector": "button[data-testid='sign-in-button']",
                "input_value": None,
            }
        }


class ExecutionResultResponse(BaseModel):
    """Comprehensive execution results after completion."""

    execution_id: str = Field(description="Unique identifier for this execution")
    plan_id: int = Field(description="ID of the ExecutionPlan that was executed")
    status: str = Field(description="Final execution status")
    success: bool = Field(description="Whether execution was successful overall")
    started_at: str = Field(description="When execution started (ISO format)")
    completed_at: str = Field(description="When execution completed (ISO format)")
    total_duration_seconds: float = Field(description="Total execution time in seconds")
    steps_completed: int = Field(description="Number of steps successfully completed")
    total_steps: int = Field(description="Total number of steps in the plan")
    success_rate: float = Field(description="Percentage of steps that succeeded")
    error_message: str | None = Field(
        default=None, description="Overall error message if execution failed"
    )
    action_results: list[ActionResult] = Field(
        description="Detailed results for each action step"
    )
    screenshots: list[str] = Field(description="Paths to all screenshots taken")
    performance_metrics: dict[str, Any] = Field(
        description="Performance and timing metrics"
    )
    execution_logs: list[dict[str, Any]] = Field(description="Detailed execution logs")

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_id": 123,
                "status": "completed",
                "success": True,
                "started_at": "2025-06-20T10:30:00Z",
                "completed_at": "2025-06-20T10:35:30Z",
                "total_duration_seconds": 330.5,
                "steps_completed": 8,
                "total_steps": 8,
                "success_rate": 100.0,
                "error_message": None,
                "action_results": [],
                "screenshots": [
                    "screenshots/execution_123_initial.png",
                    "screenshots/execution_123_step_1_before.png",
                    "screenshots/execution_123_step_1_after.png",
                ],
                "performance_metrics": {
                    "average_step_duration_ms": 2500,
                    "total_screenshots": 16,
                    "browser_memory_peak_mb": 245,
                },
                "execution_logs": [],
            }
        }
