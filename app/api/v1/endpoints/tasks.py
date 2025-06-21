from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.task import (
    Task, TaskCreate, TaskUpdate, TaskExecutionRequest, TaskExecutionResponse,
    TaskResult, TaskList, TaskFilters, TaskStats
)
from app.schemas.user import User
from app.services.task_service import TaskService
from app.api.dependencies import get_db, get_current_user

router = APIRouter()


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new automation task.

    Creates a task with the provided goal and configuration.
    The task will be queued for execution planning.
    """
    try:
        task = await TaskService.create_task(db, current_user.id, task_data)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.get("/", response_model=TaskList)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user's tasks with pagination and filtering.

    Returns paginated list of tasks with optional filtering by status and priority.
    """
    try:
        # Build filters
        filters = TaskFilters()
        if status:
            filters.status = status
        if priority:
            filters.priority = priority

        # Get tasks
        tasks, total_count = await TaskService.get_user_tasks(
            db, current_user.id, filters, page, page_size
        )

        # Build response
        has_next = (page * page_size) < total_count
        has_previous = page > 1

        return TaskList(
            tasks=tasks,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )


@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific task.

    Returns task details including execution plan and progress.
    """
    try:
        task = await TaskService.get_task(db, task_id, current_user.id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task"
        )


@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing task.

    Updates task configuration and settings.
    Cannot update task if it's currently executing.
    """
    try:
        task = await TaskService.update_task(db, task_id, current_user.id, task_update)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a task.

    Permanently removes a task and all associated data.
    Cannot delete task if it's currently executing.
    """
    try:
        success = await TaskService.delete_task(db, task_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


@router.get("/stats/summary", response_model=TaskStats)
async def get_task_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task statistics for the current user.

    Returns comprehensive statistics including success rates,
    completion times, and activity summaries.
    """
    try:
        stats = await TaskService.get_task_stats(db, current_user.id, days)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task statistics"
        )


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """
    Delete a task.
    
    Cancels execution if running and removes from database.
    """
    # TODO: Implement task deletion
    # - Validate user owns task
    # - Cancel if executing
    # - Delete from database
    # - Cleanup resources
    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/execute", response_model=TaskExecutionResponse)
async def execute_task(task_id: int, execution_request: TaskExecutionRequest):
    """
    Execute a task.
    
    Starts task execution with the configured execution plan.
    """
    # TODO: Implement task execution
    # - Validate task exists and user owns it
    # - Check execution plan exists
    # - Queue for execution
    # - Return execution response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Task execution not yet implemented"
    )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int):
    """
    Cancel a running task.
    
    Stops task execution and cleans up resources.
    """
    # TODO: Implement task cancellation
    # - Validate user owns task
    # - Cancel execution
    # - Update task status
    # - Cleanup resources
    return {"message": "Task cancelled successfully"}


@router.get("/{task_id}/result", response_model=TaskResult)
async def get_task_result(task_id: int):
    """
    Get task execution result.
    
    Returns the final result and extracted data from task execution.
    """
    # TODO: Implement result retrieval
    # - Validate user owns task
    # - Get execution result
    # - Return result data
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Task result retrieval not yet implemented"
    )


@router.get("/stats", response_model=TaskStats)
async def get_task_stats():
    """
    Get user's task execution statistics.
    
    Returns success rates, common domains, and activity metrics.
    """
    # TODO: Implement stats calculation
    # - Get current user
    # - Calculate statistics
    # - Return stats
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Task statistics not yet implemented"
    )
