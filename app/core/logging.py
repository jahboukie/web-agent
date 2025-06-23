import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                structlog.processors.JSONRenderer()
                if settings.LOG_FORMAT == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Suppress noisy loggers in production
    if settings.ENVIRONMENT == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class RequestContextMiddleware:
    """Middleware to add request context to logs."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add request context to structlog context
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                request_id=scope.get("request_id"),
                method=scope.get("method"),
                path=scope.get("path"),
                user_id=scope.get("user_id"),
            )

        await self.app(scope, receive, send)
