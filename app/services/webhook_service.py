import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert

from app.core.config import settings
from app.core.logging import get_logger
from app.core.http_client import http_client_manager
from app.models.user import User

logger = get_logger(__name__)


class WebhookDelivery:
    """Represents a webhook delivery attempt."""
    
    def __init__(self, webhook_id: str, url: str, payload: Dict[str, Any]):
        self.webhook_id = webhook_id
        self.url = url
        self.payload = payload
        self.attempt_count = 0
        self.max_attempts = 5
        self.created_at = datetime.utcnow()
        self.last_attempt_at: Optional[datetime] = None
        self.success = False
        self.error_message: Optional[str] = None
        self.response_status: Optional[int] = None
        self.response_body: Optional[str] = None


class WebhookService:
    """
    Phase 2D: Webhook service for notifying external systems about execution completion.
    
    Perfect for integration with n8n, Zapier, Make.com, and other automation platforms.
    Provides reliable delivery with retry logic and comprehensive logging.
    """
    
    def __init__(self):
        self.pending_deliveries: Dict[str, WebhookDelivery] = {}
        self.delivery_queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self._initialized = False

        logger.info("WebhookService initialized")
    
    async def initialize(self):
        """Initialize the webhook service."""
        if self._initialized:
            return

        # Ensure HTTP client manager is initialized
        if not http_client_manager.is_initialized:
            raise RuntimeError("HTTP client manager must be initialized before webhook service")

        # Start webhook delivery worker
        self.worker_task = asyncio.create_task(self._webhook_delivery_worker())

        self._initialized = True
        logger.info("WebhookService initialized with delivery worker")
    
    async def shutdown(self):
        """Shutdown the webhook service."""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        self._initialized = False
        logger.info("WebhookService shutdown complete")
    
    async def send_execution_completion_webhook(
        self,
        user_id: int,
        execution_id: str,
        plan_id: int,
        success: bool,
        execution_results: Dict[str, Any],
        webhook_urls: Optional[List[str]] = None
    ) -> None:
        """
        Send webhook notifications for execution completion.
        
        Args:
            user_id: ID of the user who owns the execution
            execution_id: Unique execution identifier
            plan_id: ID of the executed plan
            success: Whether execution was successful
            execution_results: Detailed execution results
            webhook_urls: Optional list of webhook URLs (if not provided, will fetch from user settings)
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get webhook URLs if not provided
            if not webhook_urls:
                webhook_urls = await self._get_user_webhook_urls(user_id)
            
            if not webhook_urls:
                logger.debug(f"No webhook URLs configured for user {user_id}")
                return
            
            # Create webhook payload
            payload = {
                "event": "execution_completed",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "execution_id": execution_id,
                    "plan_id": plan_id,
                    "user_id": user_id,
                    "success": success,
                    "status": "completed" if success else "failed",
                    "execution_results": execution_results,
                    "webhook_version": "1.0"
                }
            }
            
            # Queue webhook deliveries
            for url in webhook_urls:
                if self._is_valid_webhook_url(url):
                    webhook_id = str(uuid.uuid4())
                    delivery = WebhookDelivery(webhook_id, url, payload)
                    self.pending_deliveries[webhook_id] = delivery
                    await self.delivery_queue.put(webhook_id)
                    
                    logger.info(
                        "Webhook delivery queued",
                        webhook_id=webhook_id,
                        url=url,
                        execution_id=execution_id
                    )
                else:
                    logger.warning(f"Invalid webhook URL skipped: {url}")
            
        except Exception as e:
            logger.error(
                "Failed to send execution completion webhook",
                user_id=user_id,
                execution_id=execution_id,
                error=str(e)
            )
    
    async def send_execution_progress_webhook(
        self,
        user_id: int,
        execution_id: str,
        plan_id: int,
        current_step: int,
        total_steps: int,
        progress_percentage: int,
        webhook_urls: Optional[List[str]] = None
    ) -> None:
        """Send webhook notifications for execution progress updates."""
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get webhook URLs if not provided
            if not webhook_urls:
                webhook_urls = await self._get_user_webhook_urls(user_id)
            
            if not webhook_urls:
                return
            
            # Create progress payload
            payload = {
                "event": "execution_progress",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "execution_id": execution_id,
                    "plan_id": plan_id,
                    "user_id": user_id,
                    "current_step": current_step,
                    "total_steps": total_steps,
                    "progress_percentage": progress_percentage,
                    "status": "executing",
                    "webhook_version": "1.0"
                }
            }
            
            # Queue webhook deliveries (only for URLs that want progress updates)
            for url in webhook_urls:
                if self._is_valid_webhook_url(url) and self._wants_progress_updates(url):
                    webhook_id = str(uuid.uuid4())
                    delivery = WebhookDelivery(webhook_id, url, payload)
                    self.pending_deliveries[webhook_id] = delivery
                    await self.delivery_queue.put(webhook_id)
            
        except Exception as e:
            logger.error(
                "Failed to send execution progress webhook",
                user_id=user_id,
                execution_id=execution_id,
                error=str(e)
            )
    
    def _is_valid_webhook_url(self, url: str) -> bool:
        """Validate webhook URL format and security."""
        try:
            parsed = urlparse(url)
            
            # Must be HTTP or HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Must have a valid hostname
            if not parsed.hostname:
                return False
            
            # Block localhost and private IPs in production
            if settings.ENVIRONMENT == "production":
                if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                    return False
                
                # Block private IP ranges
                if parsed.hostname.startswith(('10.', '172.', '192.168.')):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _wants_progress_updates(self, url: str) -> bool:
        """Check if webhook URL wants progress updates (simple heuristic)."""
        # This is a simple implementation - in production you might want
        # to store this preference in user settings
        return "progress" in url.lower() or "realtime" in url.lower()
    
    async def _get_user_webhook_urls(self, user_id: int) -> List[str]:
        """Get webhook URLs for a user from database or settings."""
        # This is a placeholder - in a real implementation you would
        # fetch this from user preferences or a webhooks table
        # For now, return empty list
        return []

    async def _webhook_delivery_worker(self):
        """Background worker that processes webhook deliveries."""
        logger.info("Webhook delivery worker started")

        while True:
            try:
                # Wait for webhook delivery
                webhook_id = await self.delivery_queue.get()

                if webhook_id not in self.pending_deliveries:
                    continue

                delivery = self.pending_deliveries[webhook_id]

                # Attempt delivery
                success = await self._attempt_webhook_delivery(delivery)

                if success:
                    # Remove from pending deliveries
                    del self.pending_deliveries[webhook_id]
                    logger.info(
                        "Webhook delivered successfully",
                        webhook_id=webhook_id,
                        url=delivery.url,
                        attempts=delivery.attempt_count
                    )
                else:
                    # Check if we should retry
                    if delivery.attempt_count < delivery.max_attempts:
                        # Schedule retry with exponential backoff
                        retry_delay = min(300, 2 ** delivery.attempt_count)  # Max 5 minutes
                        asyncio.create_task(
                            self._schedule_retry(webhook_id, retry_delay)
                        )
                        logger.warning(
                            "Webhook delivery failed, scheduling retry",
                            webhook_id=webhook_id,
                            url=delivery.url,
                            attempts=delivery.attempt_count,
                            retry_in_seconds=retry_delay
                        )
                    else:
                        # Max attempts reached, give up
                        del self.pending_deliveries[webhook_id]
                        logger.error(
                            "Webhook delivery failed permanently",
                            webhook_id=webhook_id,
                            url=delivery.url,
                            attempts=delivery.attempt_count,
                            error=delivery.error_message
                        )

                # Mark task as done
                self.delivery_queue.task_done()

            except asyncio.CancelledError:
                logger.info("Webhook delivery worker cancelled")
                break
            except Exception as e:
                logger.error("Webhook delivery worker error", error=str(e))
                await asyncio.sleep(1)  # Brief pause before continuing

    async def _attempt_webhook_delivery(self, delivery: WebhookDelivery) -> bool:
        """Attempt to deliver a webhook."""
        delivery.attempt_count += 1
        delivery.last_attempt_at = datetime.utcnow()

        try:
            # Get the shared HTTP session
            session = http_client_manager.session

            # Prepare request headers
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-ID": delivery.webhook_id,
                "X-Webhook-Attempt": str(delivery.attempt_count),
                "X-Webhook-Timestamp": delivery.created_at.isoformat(),
                "X-WebAgent-Version": settings.APP_VERSION
            }

            # Send webhook
            async with session.post(
                delivery.url,
                json=delivery.payload,
                headers=headers
            ) as response:
                delivery.response_status = response.status
                delivery.response_body = await response.text()

                # Consider 2xx status codes as success
                if 200 <= response.status < 300:
                    delivery.success = True
                    return True
                else:
                    delivery.error_message = f"HTTP {response.status}: {delivery.response_body[:200]}"
                    return False

        except asyncio.TimeoutError:
            delivery.error_message = "Request timeout"
            return False
        except aiohttp.ClientError as e:
            delivery.error_message = f"Client error: {str(e)}"
            return False
        except Exception as e:
            delivery.error_message = f"Unexpected error: {str(e)}"
            return False

    async def _schedule_retry(self, webhook_id: str, delay_seconds: int):
        """Schedule a webhook retry after a delay."""
        await asyncio.sleep(delay_seconds)

        # Check if delivery is still pending
        if webhook_id in self.pending_deliveries:
            await self.delivery_queue.put(webhook_id)

    async def get_delivery_status(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a webhook delivery."""
        if webhook_id not in self.pending_deliveries:
            return None

        delivery = self.pending_deliveries[webhook_id]

        return {
            "webhook_id": webhook_id,
            "url": delivery.url,
            "attempt_count": delivery.attempt_count,
            "max_attempts": delivery.max_attempts,
            "created_at": delivery.created_at.isoformat(),
            "last_attempt_at": delivery.last_attempt_at.isoformat() if delivery.last_attempt_at else None,
            "success": delivery.success,
            "error_message": delivery.error_message,
            "response_status": delivery.response_status,
            "status": "completed" if delivery.success else "pending" if delivery.attempt_count < delivery.max_attempts else "failed"
        }


# Global service instance
webhook_service = WebhookService()
