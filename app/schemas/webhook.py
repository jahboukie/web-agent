from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class WebhookConfigRequest(BaseModel):
    """Request to configure webhook URLs for a user."""

    webhook_urls: list[str] = Field(
        description="List of webhook URLs to receive notifications",
        min_items=1,
        max_items=10,
    )
    events: list[str] = Field(
        default=["execution_completed"], description="List of events to subscribe to"
    )

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        valid_events = [
            "execution_completed",
            "execution_progress",
            "execution_started",
        ]
        for event in v:
            if event not in valid_events:
                raise ValueError(
                    f"Invalid event: {event}. Valid events: {valid_events}"
                )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "webhook_urls": [
                    "https://hooks.zapier.com/hooks/catch/123456/abcdef/",
                    "https://your-n8n-instance.com/webhook/webagent-execution",
                ],
                "events": ["execution_completed", "execution_progress"],
            }
        }


class WebhookConfigResponse(BaseModel):
    """Response after configuring webhooks."""

    user_id: int = Field(description="ID of the user")
    webhook_urls: list[str] = Field(description="Configured webhook URLs")
    events: list[str] = Field(description="Subscribed events")
    message: str = Field(description="Configuration result message")
    configured_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the configuration was updated",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "webhook_urls": ["https://hooks.zapier.com/hooks/catch/123456/abcdef/"],
                "events": ["execution_completed"],
                "message": "Successfully configured 1 webhook URLs",
                "configured_at": "2025-06-20T10:30:00Z",
            }
        }


class WebhookTestRequest(BaseModel):
    """Request to test a webhook URL."""

    webhook_url: str = Field(description="Webhook URL to test")

    class Config:
        json_schema_extra = {
            "example": {
                "webhook_url": "https://hooks.zapier.com/hooks/catch/123456/abcdef/"
            }
        }


class WebhookTestResponse(BaseModel):
    """Response from testing a webhook."""

    webhook_url: str = Field(description="Tested webhook URL")
    success: bool = Field(description="Whether the test was successful")
    response_status: int | None = Field(
        default=None, description="HTTP response status code"
    )
    response_body: str | None = Field(
        default=None, description="HTTP response body (truncated)"
    )
    error_message: str | None = Field(
        default=None, description="Error message if test failed"
    )
    test_payload: dict[str, Any] = Field(description="Payload that was sent")
    tested_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the test was performed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "webhook_url": "https://hooks.zapier.com/hooks/catch/123456/abcdef/",
                "success": True,
                "response_status": 200,
                "response_body": "OK",
                "error_message": None,
                "test_payload": {"event": "webhook_test", "data": {"test": True}},
                "tested_at": "2025-06-20T10:30:00Z",
            }
        }


class WebhookDeliveryStatus(BaseModel):
    """Status of a webhook delivery attempt."""

    webhook_id: str = Field(description="Unique webhook delivery ID")
    url: str = Field(description="Webhook URL")
    attempt_count: int = Field(description="Number of delivery attempts")
    max_attempts: int = Field(description="Maximum number of attempts")
    created_at: str = Field(description="When the delivery was created")
    last_attempt_at: str | None = Field(
        default=None, description="When the last attempt was made"
    )
    success: bool = Field(description="Whether delivery was successful")
    error_message: str | None = Field(
        default=None, description="Error message if delivery failed"
    )
    response_status: int | None = Field(
        default=None, description="HTTP response status from last attempt"
    )
    status: str = Field(description="Overall delivery status")

    class Config:
        json_schema_extra = {
            "example": {
                "webhook_id": "550e8400-e29b-41d4-a716-446655440000",
                "url": "https://hooks.zapier.com/hooks/catch/123456/abcdef/",
                "attempt_count": 2,
                "max_attempts": 5,
                "created_at": "2025-06-20T10:30:00Z",
                "last_attempt_at": "2025-06-20T10:31:00Z",
                "success": False,
                "error_message": "HTTP 500: Internal Server Error",
                "response_status": 500,
                "status": "pending",
            }
        }


class WebhookEventPayload(BaseModel):
    """Standard webhook event payload structure."""

    event: str = Field(description="Event type")
    timestamp: str = Field(description="Event timestamp in ISO format")
    data: dict[str, Any] = Field(description="Event-specific data")
    webhook_version: str = Field(default="1.0", description="Webhook payload version")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "execution_completed",
                "timestamp": "2025-06-20T10:30:00Z",
                "data": {
                    "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                    "plan_id": 123,
                    "user_id": 456,
                    "success": True,
                    "status": "completed",
                    "execution_results": {
                        "steps_completed": 8,
                        "total_steps": 8,
                        "success_rate": 100.0,
                        "total_duration_seconds": 45.2,
                    },
                },
                "webhook_version": "1.0",
            }
        }


class WebhookExecutionCompletedData(BaseModel):
    """Data structure for execution_completed webhook events."""

    execution_id: str = Field(description="Unique execution identifier")
    plan_id: int = Field(description="ID of the executed plan")
    user_id: int = Field(description="ID of the user who owns the execution")
    success: bool = Field(description="Whether execution was successful")
    status: str = Field(description="Final execution status")
    execution_results: dict[str, Any] = Field(description="Detailed execution results")

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_id": 123,
                "user_id": 456,
                "success": True,
                "status": "completed",
                "execution_results": {
                    "steps_completed": 8,
                    "total_steps": 8,
                    "success_rate": 100.0,
                    "total_duration_seconds": 45.2,
                    "screenshots": ["screenshot1.png", "screenshot2.png"],
                },
            }
        }


class WebhookExecutionProgressData(BaseModel):
    """Data structure for execution_progress webhook events."""

    execution_id: str = Field(description="Unique execution identifier")
    plan_id: int = Field(description="ID of the executing plan")
    user_id: int = Field(description="ID of the user who owns the execution")
    current_step: int = Field(description="Current step number")
    total_steps: int = Field(description="Total number of steps")
    progress_percentage: int = Field(description="Progress percentage (0-100)")
    status: str = Field(description="Current execution status")

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_id": 123,
                "user_id": 456,
                "current_step": 3,
                "total_steps": 8,
                "progress_percentage": 37,
                "status": "executing",
            }
        }
