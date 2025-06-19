from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
import structlog
import time
import uuid

from app.core.config import settings
from app.core.logging import configure_logging, RequestContextMiddleware
from app.api.v1.router import api_router

# Configure logging before creating the app
configure_logging()
logger = structlog.get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="WebAgent: AI system for automated web task execution",
        openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # Add security middleware (disabled for development)
    # app.add_middleware(
    #     TrustedHostMiddleware,
    #     allowed_hosts=["*"] if settings.DEBUG else ["yourdomain.com"]
    # )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Add request context middleware
    app.add_middleware(RequestContextMiddleware)
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    return app


app = create_application()


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request."""
    request_id = str(uuid.uuid4())
    request.scope["request_id"] = request_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time,
        request_id=request_id,
    )
    
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging."""
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        method=request.method,
        url=str(request.url),
        request_id=request.scope.get("request_id"),
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "request_id": request.scope.get("request_id"),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.error(
        "Validation error occurred",
        errors=exc.errors(),
        method=request.method,
        url=str(request.url),
        request_id=request.scope.get("request_id"),
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": exc.errors(),
                "request_id": request.scope.get("request_id"),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(
        "Unexpected error occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        method=request.method,
        url=str(request.url),
        request_id=request.scope.get("request_id"),
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError", 
                "message": "An unexpected error occurred",
                "request_id": request.scope.get("request_id"),
            }
        },
    )


@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info(
        "WebAgent starting up",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        version=settings.APP_VERSION,
    )

    # Fix Windows event loop policy for Playwright
    import sys
    import asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Set Windows ProactorEventLoopPolicy for Playwright compatibility")

    # Initialize database
    try:
        from app.db.session import get_async_session, check_database_connection
        from app.db.init_db import init_db

        # Check database connection
        if await check_database_connection():
            logger.info("Database connection successful")

            # Initialize database with required data
            async for db in get_async_session():
                await init_db(db)
                break
        else:
            logger.error("Database connection failed")

    except Exception as e:
        logger.error("Database initialization failed", error=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("WebAgent shutting down")

    # Close database connections
    try:
        from app.db.session import close_async_engine
        await close_async_engine()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to WebAgent API",
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs" if settings.DEBUG else None,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {"status": "unknown"}
    }

    # Check database health
    try:
        from app.db.session import get_async_session
        from app.db.init_db import check_database_health

        async for db in get_async_session():
            db_health = await check_database_health(db)
            health_status["database"] = db_health

            if not db_health.get("database_connection", False):
                health_status["status"] = "degraded"
            break

    except Exception as e:
        health_status["database"] = {"status": "error", "error": str(e)}
        health_status["status"] = "degraded"

    return health_status