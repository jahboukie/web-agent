"""
Browser Pool Manager for efficient browser context management.

This module provides:
- Browser context pooling for resource efficiency
- Anti-detection features and stealth mode
- Resource monitoring and cleanup
- Context lifecycle management
- Performance optimization
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import psutil
import structlog
from playwright.async_api import Browser, BrowserContext, async_playwright

from app.core.config import settings

logger = structlog.get_logger(__name__)


class BrowserPoolManager:
    """Manages a pool of browser contexts for efficient resource utilization."""

    def __init__(self):
        self.pool_size = getattr(settings, "BROWSER_POOL_SIZE", 5)
        self.max_context_age_minutes = getattr(
            settings, "BROWSER_CONTEXT_MAX_AGE_MINUTES", 30
        )
        self.max_memory_mb = getattr(settings, "BROWSER_MAX_MEMORY_MB", 512)

        # Pool management
        self.available_contexts: asyncio.Queue = asyncio.Queue(maxsize=self.pool_size)
        self.active_contexts: dict[str, dict] = {}  # context_id -> context_info
        self.browser: Browser | None = None
        self.playwright = None

        # Stats
        self.contexts_created = 0
        self.contexts_reused = 0
        self.contexts_cleanup = 0

        # Cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._initialized = False

    async def initialize(self):
        """Initialize the browser pool."""
        if self._initialized:
            return

        try:
            self.playwright = await async_playwright().start()

            # Launch browser with optimized settings
            self.browser = await self.playwright.chromium.launch(
                headless=getattr(settings, "HEADLESS", True),
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-default-apps",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                    "--memory-pressure-off",
                    f"--max_old_space_size={self.max_memory_mb}",
                    "--disable-web-security",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                ],
            )

            # Pre-warm the pool with contexts
            await self._populate_pool()

            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

            self._initialized = True
            logger.info("Browser pool initialized", pool_size=self.pool_size)

        except Exception as e:
            logger.error("Failed to initialize browser pool", error=str(e))
            raise

    async def _populate_pool(self):
        """Pre-populate the pool with browser contexts."""
        for _ in range(self.pool_size):
            try:
                context = await self._create_context()
                await self.available_contexts.put(context)
            except Exception as e:
                logger.error("Failed to create initial context", error=str(e))
                break

    async def _create_context(self) -> dict[str, Any]:
        """Create a new browser context with anti-detection features."""
        if not self.browser:
            raise RuntimeError("Browser not initialized")

        context_id = str(uuid.uuid4())

        # Anti-detection context options
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        }

        # Create context
        browser_context = await self.browser.new_context(**context_options)

        # Add stealth scripts
        await browser_context.add_init_script(
            """
            // Override the navigator.webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // Override the navigator.plugins property
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Override the navigator.languages property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            // Override the screen properties
            Object.defineProperty(screen, 'colorDepth', {
                get: () => 24,
            });
        """
        )

        context_info = {
            "id": context_id,
            "context": browser_context,
            "created_at": datetime.utcnow(),
            "last_used_at": datetime.utcnow(),
            "usage_count": 0,
            "current_task_id": None,
            "memory_usage_mb": 0,
        }

        self.contexts_created += 1
        logger.debug("Created new browser context", context_id=context_id)

        return context_info

    async def acquire_context(self, task_id: int) -> BrowserContext:
        """Acquire a browser context for task execution."""
        if not self._initialized:
            await self.initialize()

        try:
            # Try to get an available context
            try:
                context_info = await asyncio.wait_for(
                    self.available_contexts.get(), timeout=10.0
                )
                self.contexts_reused += 1
            except TimeoutError:
                # Create new context if pool is empty
                context_info = await self._create_context()
                logger.warning(
                    "Created new context due to pool exhaustion", task_id=task_id
                )

            # Update context info
            context_info["current_task_id"] = task_id
            context_info["last_used_at"] = datetime.utcnow()
            context_info["usage_count"] += 1

            # Store in active contexts
            self.active_contexts[context_info["id"]] = context_info

            logger.info(
                "Browser context acquired",
                task_id=task_id,
                context_id=context_info["id"],
                usage_count=context_info["usage_count"],
            )

            return context_info["context"]

        except Exception as e:
            logger.error(
                "Failed to acquire browser context", task_id=task_id, error=str(e)
            )
            raise

    async def release_context(self, task_id: int, context: BrowserContext):
        """Release browser context back to pool or cleanup."""
        context_info = None

        # Find the context info
        for ctx_id, ctx_info in self.active_contexts.items():
            if ctx_info["context"] == context:
                context_info = ctx_info
                break

        if not context_info:
            logger.warning("Context not found in active contexts", task_id=task_id)
            return

        try:
            # Check if context should be cleaned up
            age_minutes = (
                datetime.utcnow() - context_info["created_at"]
            ).total_seconds() / 60
            should_cleanup = (
                age_minutes > self.max_context_age_minutes
                or context_info["usage_count"] > 50
                or await self._check_memory_usage(context_info)
            )

            if should_cleanup:
                await self._cleanup_context(context_info)
                logger.info(
                    "Context cleaned up",
                    task_id=task_id,
                    context_id=context_info["id"],
                    age_minutes=round(age_minutes, 2),
                )
            else:
                # Reset context state and return to pool
                await self._reset_context(context_info)
                context_info["current_task_id"] = None

                # Remove from active and return to available
                del self.active_contexts[context_info["id"]]

                try:
                    await self.available_contexts.put(context_info)
                    logger.debug(
                        "Context returned to pool", context_id=context_info["id"]
                    )
                except asyncio.QueueFull:
                    # Pool is full, cleanup this context
                    await self._cleanup_context(context_info)
                    logger.debug(
                        "Pool full, context cleaned up", context_id=context_info["id"]
                    )

        except Exception as e:
            logger.error("Error releasing context", task_id=task_id, error=str(e))
            # Ensure cleanup on error
            await self._cleanup_context(context_info)

    async def _reset_context(self, context_info: dict[str, Any]):
        """Reset context state for reuse."""
        try:
            context = context_info["context"]

            # Close all pages except one
            pages = context.pages
            for page in pages[1:]:  # Keep first page
                await page.close()

            # Reset the remaining page
            if pages:
                page = pages[0]
                await page.goto("about:blank")
                await page.evaluate("localStorage.clear()")
                await page.evaluate("sessionStorage.clear()")

            context_info["last_used_at"] = datetime.utcnow()

        except Exception as e:
            logger.error(
                "Failed to reset context", context_id=context_info["id"], error=str(e)
            )
            raise

    async def _cleanup_context(self, context_info: dict[str, Any]):
        """Clean up browser context resources."""
        try:
            context = context_info["context"]
            await context.close()

            # Remove from active contexts if present
            if context_info["id"] in self.active_contexts:
                del self.active_contexts[context_info["id"]]

            self.contexts_cleanup += 1
            logger.debug("Context cleaned up", context_id=context_info["id"])

        except Exception as e:
            logger.error(
                "Failed to cleanup context", context_id=context_info["id"], error=str(e)
            )

    async def _check_memory_usage(self, context_info: dict[str, Any]) -> bool:
        """Check if context is using too much memory."""
        try:
            # Get current process memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            context_info["memory_usage_mb"] = int(memory_mb)

            # Check if we're over the limit
            return memory_mb > self.max_memory_mb

        except Exception as e:
            logger.error("Failed to check memory usage", error=str(e))
            return False

    async def _periodic_cleanup(self):
        """Periodic cleanup task for stale contexts."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes

                current_time = datetime.utcnow()
                stale_contexts = []

                # Check active contexts for staleness
                for ctx_id, ctx_info in list(self.active_contexts.items()):
                    age_minutes = (
                        current_time - ctx_info["last_used_at"]
                    ).total_seconds() / 60
                    if (
                        age_minutes > self.max_context_age_minutes * 2
                    ):  # Double the normal age limit
                        stale_contexts.append(ctx_info)

                # Cleanup stale contexts
                for ctx_info in stale_contexts:
                    await self._cleanup_context(ctx_info)
                    logger.warning(
                        "Cleaned up stale active context", context_id=ctx_info["id"]
                    )

                # Check available contexts queue
                available_contexts = []
                while not self.available_contexts.empty():
                    try:
                        ctx_info = self.available_contexts.get_nowait()
                        age_minutes = (
                            current_time - ctx_info["created_at"]
                        ).total_seconds() / 60

                        if age_minutes <= self.max_context_age_minutes:
                            available_contexts.append(ctx_info)
                        else:
                            await self._cleanup_context(ctx_info)
                            logger.debug(
                                "Cleaned up aged available context",
                                context_id=ctx_info["id"],
                            )
                    except asyncio.QueueEmpty:
                        break

                # Put back valid contexts
                for ctx_info in available_contexts:
                    try:
                        await self.available_contexts.put(ctx_info)
                    except asyncio.QueueFull:
                        await self._cleanup_context(ctx_info)

                logger.debug(
                    "Periodic cleanup completed",
                    active_contexts=len(self.active_contexts),
                    available_contexts=self.available_contexts.qsize(),
                    stale_cleaned=len(stale_contexts),
                )

            except Exception as e:
                logger.error("Error in periodic cleanup", error=str(e))

    async def get_pool_stats(self) -> dict[str, Any]:
        """Get browser pool statistics."""
        try:
            # Calculate memory usage
            total_memory_mb = 0
            for ctx_info in self.active_contexts.values():
                total_memory_mb += ctx_info.get("memory_usage_mb", 0)

            return {
                "pool_size": self.pool_size,
                "active_contexts": len(self.active_contexts),
                "available_contexts": self.available_contexts.qsize(),
                "total_contexts_created": self.contexts_created,
                "total_contexts_reused": self.contexts_reused,
                "total_contexts_cleaned": self.contexts_cleanup,
                "total_memory_usage_mb": total_memory_mb,
                "max_memory_mb": self.max_memory_mb,
                "max_context_age_minutes": self.max_context_age_minutes,
                "initialized": self._initialized,
            }
        except Exception as e:
            logger.error("Failed to get pool stats", error=str(e))
            return {"error": str(e)}

    async def shutdown(self):
        """Shutdown the browser pool and cleanup all resources."""
        try:
            logger.info("Shutting down browser pool")

            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Cleanup all active contexts
            for ctx_info in list(self.active_contexts.values()):
                await self._cleanup_context(ctx_info)

            # Cleanup all available contexts
            while not self.available_contexts.empty():
                try:
                    ctx_info = self.available_contexts.get_nowait()
                    await self._cleanup_context(ctx_info)
                except asyncio.QueueEmpty:
                    break

            # Close browser
            if self.browser:
                await self.browser.close()

            # Stop playwright
            if self.playwright:
                await self.playwright.stop()

            self._initialized = False
            logger.info("Browser pool shutdown completed")

        except Exception as e:
            logger.error("Error during browser pool shutdown", error=str(e))


# Global browser pool instance
browser_pool = BrowserPoolManager()
