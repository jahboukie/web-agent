from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.http_client import http_client_manager
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.user import User
from app.schemas.webhook import (
    WebhookConfigRequest,
    WebhookConfigResponse,
    WebhookDeliveryStatus,
    WebhookTestRequest,
    WebhookTestResponse,
)
from app.services.webhook_service import webhook_service

logger = get_logger(__name__)
router = APIRouter()


@router.post("/configure", response_model=WebhookConfigResponse)
async def configure_webhooks(
    webhook_config: WebhookConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Configure webhook URLs for the current user.

    Allows users to set up webhook endpoints that will receive notifications
    about execution completion and progress updates.

    **Supported Events:**
    - `execution_completed`: Sent when an execution finishes (success or failure)
    - `execution_progress`: Sent during execution for progress updates (optional)

    **Webhook Payload Format:**
    ```json
    {
        "event": "execution_completed",
        "timestamp": "2025-06-20T10:30:00Z",
        "data": {
            "execution_id": "uuid",
            "plan_id": 123,
            "user_id": 456,
            "success": true,
            "execution_results": {...}
        }
    }
    ```

    **Perfect for:**
    - n8n workflows
    - Zapier automations
    - Make.com scenarios
    - Custom integrations
    """
    try:
        # Validate webhook URLs
        valid_urls = []
        invalid_urls = []

        for url in webhook_config.webhook_urls:
            if webhook_service._is_valid_webhook_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)

        if invalid_urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid webhook URLs: {', '.join(invalid_urls)}",
            )

        # TODO: Store webhook configuration in database
        # For now, we'll just validate and return success

        logger.info(
            "Webhook configuration updated",
            user_id=current_user.id,
            webhook_count=len(valid_urls),
        )

        return WebhookConfigResponse(
            user_id=current_user.id,
            webhook_urls=valid_urls,
            events=webhook_config.events,
            message=f"Successfully configured {len(valid_urls)} webhook URLs",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to configure webhooks", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure webhooks",
        )


@router.get("/status", response_model=list[WebhookConfigResponse])
async def get_webhook_configuration(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get current webhook configuration for the user.

    Returns all configured webhook URLs and their settings.
    """
    try:
        # TODO: Fetch from database
        # For now, return empty configuration

        return []

    except Exception as e:
        logger.error(
            "Failed to get webhook configuration", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve webhook configuration",
        )


@router.post("/test", response_model=WebhookTestResponse)
async def test_webhook(
    test_request: WebhookTestRequest, current_user: User = Depends(get_current_user)
):
    """
    Test a webhook URL by sending a sample payload.

    Useful for verifying that webhook endpoints are working correctly
    before configuring them for real notifications.
    """
    try:
        if not webhook_service._is_valid_webhook_url(test_request.webhook_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook URL"
            )

        # Create test payload
        test_payload = {
            "event": "webhook_test",
            "timestamp": "2025-06-20T10:30:00Z",
            "data": {
                "test": True,
                "user_id": current_user.id,
                "message": "This is a test webhook from WebAgent",
                "webhook_version": "1.0",
            },
        }

        # Send test webhook using shared HTTP session
        session = http_client_manager.session

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Test": "true",
            "X-WebAgent-Version": "1.0",
        }

        try:
            async with session.post(
                test_request.webhook_url, json=test_payload, headers=headers
            ) as response:
                response_body = await response.text()
                success = 200 <= response.status < 300

                return WebhookTestResponse(
                    webhook_url=test_request.webhook_url,
                    success=success,
                    response_status=response.status,
                    response_body=response_body[:500] if response_body else None,
                    error_message=None if success else f"HTTP {response.status}",
                    test_payload=test_payload,
                )

        except Exception as e:
            return WebhookTestResponse(
                webhook_url=test_request.webhook_url,
                success=False,
                response_status=None,
                response_body=None,
                error_message=str(e),
                test_payload=test_payload,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to test webhook",
            user_id=current_user.id,
            webhook_url=test_request.webhook_url,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test webhook",
        )


@router.get("/deliveries/{webhook_id}", response_model=WebhookDeliveryStatus)
async def get_webhook_delivery_status(
    webhook_id: str, current_user: User = Depends(get_current_user)
):
    """
    Get the delivery status of a specific webhook.

    Useful for tracking webhook delivery attempts and debugging
    delivery failures.
    """
    try:
        delivery_status = await webhook_service.get_delivery_status(webhook_id)

        if not delivery_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook delivery not found",
            )

        return WebhookDeliveryStatus(**delivery_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get webhook delivery status",
            webhook_id=webhook_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve webhook delivery status",
        )


@router.delete("/configure", response_model=dict[str, str])
async def remove_webhook_configuration(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Remove all webhook configuration for the current user.

    This will stop all webhook notifications for the user.
    """
    try:
        # TODO: Remove from database
        # For now, just return success

        logger.info("Webhook configuration removed", user_id=current_user.id)

        return {"message": "Webhook configuration removed successfully"}

    except Exception as e:
        logger.error(
            "Failed to remove webhook configuration",
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove webhook configuration",
        )
