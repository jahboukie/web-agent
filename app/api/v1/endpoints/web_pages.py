from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.schemas.web_page import (
    WebPage, WebPageCreate, WebPageUpdate, WebPageParseRequest, WebPageParseResponse
)
from app.schemas.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.db.session import get_async_session
from app.api.dependencies import get_current_user
from app.services.web_parser import web_parser_service
from app.services.task_status_service import TaskStatusService
from app.services.webpage_cache_service import webpage_cache_service

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _process_webpage_parsing(
    task_id: int,
    url: str,
    options: WebPageParseRequest
):
    """Background task function for webpage parsing."""

    # Get database session
    async for db in get_async_session():
        try:
            # Process the webpage
            result = await web_parser_service.parse_webpage_async(
                db, task_id, url, options
            )

            logger.info("Background webpage parsing completed", task_id=task_id, url=url)

        except Exception as e:
            logger.error("Background webpage parsing failed", task_id=task_id, url=url, error=str(e))

            # Update task status to failed
            await TaskStatusService.fail_task(db, task_id, e)

        # Always break after first iteration since we only need one session
        break


@router.post("/parse")
async def parse_webpage(
    parse_request: WebPageParseRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Parse a webpage and extract semantic information (Background Processing).

    This endpoint immediately returns a task_id and processes the webpage parsing
    in the background. Use the task_id to check status and retrieve results.

    Returns:
        - task_id: Unique identifier for tracking the parsing task
        - status: Initial status (always "queued")
        - estimated_duration_seconds: Expected time to complete
        - check_status_url: URL to check task progress
    """

    try:
        # Create task record
        task = Task(
            user_id=current_user.id,
            title=f"Parse webpage: {parse_request.url}",
            description=f"Semantic analysis and element extraction for {parse_request.url}",
            goal=f"Extract interactive elements and analyze webpage structure",
            target_url=str(parse_request.url),
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            max_retries=3,
            timeout_seconds=300,  # 5 minutes
            require_confirmation=False,
            allow_sensitive_actions=False
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)

        # Queue background processing
        background_tasks.add_task(
            _process_webpage_parsing,
            task_id=task.id,
            url=str(parse_request.url),
            options=parse_request
        )

        logger.info(
            "Webpage parsing queued",
            task_id=task.id,
            url=parse_request.url,
            user_id=current_user.id
        )

        # Return immediately with task information
        return {
            "task_id": task.id,
            "status": "queued",
            "message": "Webpage parsing started",
            "estimated_duration_seconds": 30,
            "check_status_url": f"/api/v1/parse/{task.id}",
            "url": str(parse_request.url)
        }

    except Exception as e:
        logger.error("Failed to queue webpage parsing", error=str(e), url=parse_request.url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start webpage parsing: {str(e)}"
        )


@router.get("/{task_id}")
async def get_parsing_status(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get the status of a webpage parsing task.

    Returns real-time status information including:
    - Current progress percentage
    - Current processing step
    - Estimated time remaining
    - Results (if completed)
    - Error information (if failed)
    """

    try:
        # Get task status
        task_status = await TaskStatusService.get_task_status(db, task_id, current_user.id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        # Add additional context based on status
        response = task_status.copy()

        if task_status['status'] == 'completed':
            response['message'] = "Webpage parsing completed successfully"
            response['download_results_url'] = f"/api/v1/parse/{task_id}/results"
        elif task_status['status'] == 'failed':
            response['message'] = f"Webpage parsing failed: {task_status.get('error_message', 'Unknown error')}"
            response['retry_url'] = f"/api/v1/parse/{task_id}/retry"
        elif task_status['status'] == 'in_progress':
            response['message'] = f"Processing: {task_status.get('current_step', 'Working...')}"
        else:
            response['message'] = "Task is queued for processing"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get parsing status", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status"
        )


@router.get("/{task_id}/results")
async def get_parsing_results(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get the results of a completed webpage parsing task.

    Returns the full parsing results including:
    - Interactive elements
    - Content blocks
    - Action capabilities
    - Screenshots
    - Metadata
    """

    try:
        # Get task status to verify completion
        task_status = await TaskStatusService.get_task_status(db, task_id, current_user.id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        if task_status['status'] != 'completed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task is not completed. Current status: {task_status['status']}"
            )

        # Return the result data
        result_data = task_status.get('result_data')
        if not result_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No results found for this task"
            )

        return result_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get parsing results", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve parsing results"
        )


@router.post("/{task_id}/retry")
async def retry_parsing_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retry a failed webpage parsing task.

    Resets the task status and queues it for processing again.
    """

    try:
        # Get task status
        task_status = await TaskStatusService.get_task_status(db, task_id, current_user.id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        if task_status['status'] not in ['failed', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task cannot be retried. Current status: {task_status['status']}"
            )

        # Get the original task to extract URL and options
        from sqlalchemy import select
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Reset task status
        await TaskStatusService.update_task_progress(
            db, task_id,
            status=TaskStatus.PENDING,
            progress_percentage=0,
            current_step="queued_for_retry"
        )

        # Create parse request from task data
        parse_request = WebPageParseRequest(
            url=task.target_url,
            include_screenshot=True,
            wait_for_load=2,
            wait_for_network_idle=True
        )

        # Queue background processing
        background_tasks.add_task(
            _process_webpage_parsing,
            task_id=task.id,
            url=task.target_url,
            options=parse_request
        )

        logger.info("Webpage parsing retry queued", task_id=task_id, url=task.target_url)

        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Task queued for retry",
            "check_status_url": f"/api/v1/parse/{task_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry parsing task", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry parsing task"
        )


@router.get("/active")
async def get_active_parsing_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get all active (in-progress) parsing tasks for the current user.

    Returns a list of tasks currently being processed.
    """

    try:
        active_tasks = await TaskStatusService.get_active_tasks(db, current_user.id)

        return {
            "active_tasks": active_tasks,
            "count": len(active_tasks),
            "message": f"Found {len(active_tasks)} active parsing tasks"
        }

    except Exception as e:
        logger.error("Failed to get active parsing tasks", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active tasks"
        )


@router.get("/metrics")
async def get_parsing_metrics(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get parsing task metrics for the specified time period.

    Returns statistics about task execution, success rates, and performance.
    """

    try:
        metrics = await TaskStatusService.get_task_metrics(db, current_user.id, hours)

        return metrics

    except Exception as e:
        logger.error("Failed to get parsing metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve parsing metrics"
        )


@router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get webpage parsing cache statistics.

    Returns cache performance metrics including hit rates and memory usage.
    """

    try:
        # Initialize cache service if needed
        if not webpage_cache_service._initialized:
            await webpage_cache_service.initialize()

        stats = await webpage_cache_service.get_cache_stats()

        return {
            "cache_stats": stats,
            "message": "Cache statistics retrieved successfully"
        }

    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@router.delete("/cache/{url:path}")
async def invalidate_cache(
    url: str,
    current_user: User = Depends(get_current_user)
):
    """
    Invalidate cached results for a specific URL.

    Forces re-parsing of the webpage on next request.
    """

    try:
        # Initialize cache service if needed
        if not webpage_cache_service._initialized:
            await webpage_cache_service.initialize()

        success = await webpage_cache_service.invalidate_cache(url)

        if success:
            return {
                "message": f"Cache invalidated for {url}",
                "url": url,
                "success": True
            }
        else:
            return {
                "message": f"No cache found for {url}",
                "url": url,
                "success": False
            }

    except Exception as e:
        logger.error("Failed to invalidate cache", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate cache"
        )
