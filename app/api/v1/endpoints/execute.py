from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.user import User
from app.schemas.execution import (
    ExecutionControlResponse,
    ExecutionRequest,
    ExecutionResponse,
    ExecutionResultResponse,
    ExecutionStatusResponse,
)
from app.services.action_executor import action_executor_service

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=ExecutionResponse)
async def start_execution(
    execution_request: ExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Start executing an approved ExecutionPlan.

    This endpoint takes an approved plan and begins executing it using
    browser automation. Returns immediately with an execution_id for
    tracking progress.

    **Requirements:**
    - Plan must exist and belong to the user
    - Plan must be in 'approved' status
    - User must have execution permissions

    **Process:**
    1. Validate plan exists and is approved
    2. Create execution tracking record
    3. Queue background execution
    4. Return execution_id for status tracking
    """
    try:
        logger.info(
            "Execution request received",
            plan_id=execution_request.plan_id,
            user_id=current_user.id,
        )

        # Start execution
        execution_id = await action_executor_service.execute_plan_async(
            db=db,
            plan_id=execution_request.plan_id,
            user_id=current_user.id,
            execution_options=execution_request.execution_options or {},
        )

        return ExecutionResponse(
            execution_id=execution_id,
            plan_id=execution_request.plan_id,
            status="executing",
            message="Plan execution started successfully",
            started_at=datetime.utcnow(),
            check_status_url=f"/api/v1/execute/{execution_id}",
            estimated_duration_seconds=execution_request.execution_options.get(
                "estimated_duration_seconds", 300
            ),
        )

    except ValueError as e:
        logger.warning(
            "Invalid execution request",
            plan_id=execution_request.plan_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to start execution",
            plan_id=execution_request.plan_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start plan execution",
        )


@router.get("/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: str, current_user: User = Depends(get_current_user)
):
    """
    Get real-time execution status and progress.

    Returns current status of the execution including:
    - Current step being executed
    - Progress percentage
    - Screenshots captured
    - Any errors encountered
    - Estimated time remaining

    **Status Values:**
    - `executing`: Currently running
    - `paused`: Temporarily paused
    - `completed`: Successfully finished
    - `failed`: Execution failed
    - `cancelled`: User cancelled execution
    """
    try:
        status_data = await action_executor_service.get_execution_status(execution_id)

        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
            )

        return ExecutionStatusResponse(**status_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get execution status",
            execution_id=execution_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve execution status",
        )


@router.post("/{execution_id}/pause", response_model=ExecutionControlResponse)
async def pause_execution(
    execution_id: str, current_user: User = Depends(get_current_user)
):
    """
    Pause an active execution.

    Temporarily pauses the execution after the current step completes.
    The execution can be resumed later using the resume endpoint.

    **Use Cases:**
    - User wants to review progress before continuing
    - Unexpected behavior detected
    - Need to modify execution parameters
    """
    try:
        success = await action_executor_service.pause_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or cannot be paused",
            )

        return ExecutionControlResponse(
            execution_id=execution_id,
            action="pause",
            success=True,
            message="Execution paused successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to pause execution",
            execution_id=execution_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause execution",
        )


@router.post("/{execution_id}/resume", response_model=ExecutionControlResponse)
async def resume_execution(
    execution_id: str, current_user: User = Depends(get_current_user)
):
    """
    Resume a paused execution.

    Continues execution from where it was paused. The execution will
    proceed with the next step in the plan.
    """
    try:
        success = await action_executor_service.resume_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or cannot be resumed",
            )

        return ExecutionControlResponse(
            execution_id=execution_id,
            action="resume",
            success=True,
            message="Execution resumed successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to resume execution",
            execution_id=execution_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume execution",
        )


@router.post("/{execution_id}/cancel", response_model=ExecutionControlResponse)
async def cancel_execution(
    execution_id: str, current_user: User = Depends(get_current_user)
):
    """
    Cancel an active execution.

    Immediately stops the execution and marks it as cancelled.
    This action cannot be undone.
    """
    try:
        success = await action_executor_service.cancel_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found or cannot be cancelled",
            )

        return ExecutionControlResponse(
            execution_id=execution_id,
            action="cancel",
            success=True,
            message="Execution cancelled successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to cancel execution",
            execution_id=execution_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel execution",
        )


@router.get("/{execution_id}/results", response_model=ExecutionResultResponse)
async def get_execution_results(
    execution_id: str, current_user: User = Depends(get_current_user)
):
    """
    Get detailed execution results.

    Returns comprehensive results after execution completes:
    - Final success/failure status
    - Results from each executed step
    - Screenshots captured during execution
    - Performance metrics
    - Error details if any

    **Note:** This endpoint returns detailed results only after
    execution is complete (status: completed, failed, or cancelled).
    """
    try:
        status_data = await action_executor_service.get_execution_status(execution_id)

        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found"
            )

        if status_data["status"] == "executing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Execution still in progress. Use status endpoint for real-time updates.",
            )

        # Get detailed results
        results = await action_executor_service.get_execution_results(execution_id)

        return ExecutionResultResponse(**results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get execution results",
            execution_id=execution_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve execution results",
        )
