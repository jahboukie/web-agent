"""
HTTP Client Session Manager

Provides a shared aiohttp.ClientSession for the entire application lifecycle.
Properly manages session creation on startup and cleanup on shutdown.
"""

import aiohttp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class HTTPClientManager:
    """
    Manages a shared aiohttp.ClientSession for the application.

    This ensures proper resource management and prevents the
    "Unclosed client session" warnings by maintaining a single
    session throughout the application lifecycle.
    """

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the HTTP client session on application startup."""
        if self._initialized:
            logger.warning("HTTP client already initialized")
            return

        try:
            # Create session with production-ready configuration
            timeout = aiohttp.ClientTimeout(
                total=settings.HTTP_CLIENT_TIMEOUT_TOTAL,
                connect=settings.HTTP_CLIENT_TIMEOUT_CONNECT,
                sock_read=settings.HTTP_CLIENT_TIMEOUT_READ,
            )

            # Configure headers
            headers = {
                "User-Agent": f"WebAgent/{settings.APP_VERSION}",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            # Create connector with connection pooling
            connector = aiohttp.TCPConnector(
                limit=settings.HTTP_CLIENT_CONNECTION_POOL_SIZE,
                limit_per_host=settings.HTTP_CLIENT_CONNECTION_POOL_SIZE_PER_HOST,
                ttl_dns_cache=300,  # DNS cache TTL in seconds
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=connector,
                raise_for_status=False,  # Handle status codes manually
                auto_decompress=True,
            )

            self._initialized = True

            logger.info(
                "HTTP client session initialized",
                timeout_total=settings.HTTP_CLIENT_TIMEOUT_TOTAL,
                timeout_connect=settings.HTTP_CLIENT_TIMEOUT_CONNECT,
                connection_pool_size=settings.HTTP_CLIENT_CONNECTION_POOL_SIZE,
            )

        except Exception as e:
            logger.error("Failed to initialize HTTP client session", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown the HTTP client session on application shutdown."""
        if not self._initialized or not self._session:
            logger.debug("HTTP client not initialized or already shutdown")
            return

        try:
            # Close the session gracefully
            await self._session.close()

            # Wait a bit for underlying connections to close
            import asyncio

            await asyncio.sleep(0.1)

            self._session = None
            self._initialized = False

            logger.info("HTTP client session closed gracefully")

        except Exception as e:
            logger.error("Error during HTTP client shutdown", error=str(e))

    @property
    def session(self) -> aiohttp.ClientSession:
        """
        Get the shared HTTP client session.

        Returns:
            The shared aiohttp.ClientSession instance

        Raises:
            RuntimeError: If the session is not initialized
        """
        if not self._initialized or not self._session:
            raise RuntimeError(
                "HTTP client session not initialized. "
                "Make sure to call initialize() during application startup."
            )

        return self._session

    @property
    def is_initialized(self) -> bool:
        """Check if the HTTP client session is initialized."""
        return self._initialized and self._session is not None

    async def health_check(self) -> bool:
        """
        Perform a health check on the HTTP client session.

        Returns:
            True if the session is healthy, False otherwise
        """
        if not self.is_initialized:
            return False

        try:
            # Test with a simple request to a reliable endpoint
            async with self._session.get("https://httpbin.org/status/200") as response:
                return response.status == 200
        except Exception as e:
            logger.warning("HTTP client health check failed", error=str(e))
            return False


# Global HTTP client manager instance
http_client_manager = HTTPClientManager()


async def get_http_session() -> aiohttp.ClientSession:
    """
    Dependency injection function to get the shared HTTP session.

    This can be used as a FastAPI dependency to inject the HTTP session
    into endpoints and services.

    Returns:
        The shared aiohttp.ClientSession instance

    Raises:
        RuntimeError: If the session is not initialized
    """
    return http_client_manager.session


# Convenience functions for common HTTP operations
async def http_get(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Convenience function for GET requests using the shared session."""
    session = http_client_manager.session
    return await session.get(url, **kwargs)


async def http_post(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Convenience function for POST requests using the shared session."""
    session = http_client_manager.session
    return await session.post(url, **kwargs)


async def http_put(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Convenience function for PUT requests using the shared session."""
    session = http_client_manager.session
    return await session.put(url, **kwargs)


async def http_delete(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Convenience function for DELETE requests using the shared session."""
    session = http_client_manager.session
    return await session.delete(url, **kwargs)


async def http_patch(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Convenience function for PATCH requests using the shared session."""
    session = http_client_manager.session
    return await session.patch(url, **kwargs)
