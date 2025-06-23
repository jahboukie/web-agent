"""
Task Status Service for managing task progress and lifecycle.

This service provides comprehensive task status management including:
- Real-time progress tracking
- Task state transitions
- Error handling and recovery
- Resource monitoring
- Cleanup operations
"""

from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus

logger = structlog.get_logger(__name__)


class TaskStatusService:
    """Service for managing task status and progress tracking."""

    @staticmethod
    async def update_task_progress(
        db: AsyncSession,
        task_id: int,
        status: TaskStatus | None = None,
        progress_percentage: int | None = None,
        current_step: str | None = None,
        estimated_completion: datetime | None = None,
        memory_usage_mb: int | None = None,
    ) -> bool:
        """Update task progress with real-time status."""

        try:
            # Build update data
            update_data = {"updated_at": datetime.utcnow()}

            if status is not None:
                update_data["status"] = status
            if progress_percentage is not None:
                update_data["progress_percentage"] = max(
                    0, min(100, progress_percentage)
                )
            if estimated_completion is not None:
                update_data["estimated_completion_at"] = estimated_completion
            if memory_usage_mb is not None:
                update_data["memory_usage_mb"] = memory_usage_mb

            # Update progress details
            if current_step is not None or progress_percentage is not None:
                # Get existing progress details
                result = await db.execute(
                    select(Task.progress_details).where(Task.id == task_id)
                )
                existing_details = result.scalar_one_or_none() or {}

                if current_step is not None:
                    existing_details["current_step"] = current_step
                if progress_percentage is not None:
                    existing_details["progress"] = progress_percentage
                existing_details["last_updated"] = datetime.utcnow().isoformat()

                update_data["progress_details"] = existing_details

            # Execute update
            await db.execute(update(Task).where(Task.id == task_id).values(update_data))
            await db.commit()

            logger.info(
                "Task progress updated",
                task_id=task_id,
                status=status,
                progress=progress_percentage,
                step=current_step,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to update task progress", task_id=task_id, error=str(e)
            )
            await db.rollback()
            return False

    @staticmethod
    async def mark_task_processing(
        db: AsyncSession,
        task_id: int,
        worker_id: str,
        browser_session_id: str | None = None,
    ) -> bool:
        """Mark task as actively processing."""

        try:
            update_data = {
                "status": TaskStatus.IN_PROGRESS,
                "processing_started_at": datetime.utcnow(),
                "worker_id": worker_id,
                "updated_at": datetime.utcnow(),
            }

            if browser_session_id:
                update_data["browser_session_id"] = browser_session_id

            await db.execute(update(Task).where(Task.id == task_id).values(update_data))
            await db.commit()

            logger.info(
                "Task marked as processing", task_id=task_id, worker_id=worker_id
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to mark task processing", task_id=task_id, error=str(e)
            )
            await db.rollback()
            return False

    @staticmethod
    async def complete_task(
        db: AsyncSession,
        task_id: int,
        result_data: dict[str, Any],
        performance_metrics: dict[str, Any] | None = None,
    ) -> bool:
        """Mark task as completed with results."""

        logger.info("🔧 COMPLETE_TASK: Starting complete_task", task_id=task_id)

        try:
            completion_time = datetime.utcnow()

            logger.info("🔧 COMPLETE_TASK: Getting task duration info", task_id=task_id)

            # Get task to calculate duration
            result = await db.execute(
                select(Task.processing_started_at, Task.created_at).where(
                    Task.id == task_id
                )
            )
            task_times = result.first()

            logger.info(
                "🔧 COMPLETE_TASK: Task times retrieved",
                task_id=task_id,
                has_task_times=task_times is not None,
            )

            actual_duration = None
            if task_times and task_times.processing_started_at:
                actual_duration = int(
                    (completion_time - task_times.processing_started_at).total_seconds()
                )

            update_data = {
                "status": TaskStatus.COMPLETED,
                "progress_percentage": 100,
                "processing_completed_at": completion_time,
                "completed_at": completion_time,
                "result_data": result_data,
                "updated_at": completion_time,
            }

            if actual_duration is not None:
                update_data["actual_duration_seconds"] = actual_duration

            # Add performance metrics to progress details
            if performance_metrics:
                logger.info(
                    "🔧 COMPLETE_TASK: Adding performance metrics", task_id=task_id
                )
                result = await db.execute(
                    select(Task.progress_details).where(Task.id == task_id)
                )
                existing_details = result.scalar_one_or_none() or {}
                existing_details["performance_metrics"] = performance_metrics
                existing_details["completed_at"] = completion_time.isoformat()
                update_data["progress_details"] = existing_details

            logger.info(
                "🔧 COMPLETE_TASK: About to execute database update",
                task_id=task_id,
                update_data_keys=list(update_data.keys()),
            )

            await db.execute(update(Task).where(Task.id == task_id).values(update_data))

            logger.info(
                "🔧 COMPLETE_TASK: About to commit transaction", task_id=task_id
            )
            await db.commit()
            logger.info(
                "✅ COMPLETE_TASK: Transaction committed successfully", task_id=task_id
            )

            logger.info(
                "Task completed successfully",
                task_id=task_id,
                duration_seconds=actual_duration,
                result_size=len(str(result_data)),
            )
            return True

        except Exception as e:
            logger.error(
                "❌ COMPLETE_TASK: Failed to complete task",
                task_id=task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            try:
                await db.rollback()
                logger.info(
                    "🔧 COMPLETE_TASK: Transaction rolled back", task_id=task_id
                )
            except Exception as rollback_error:
                logger.error(
                    "❌ COMPLETE_TASK: Failed to rollback transaction",
                    task_id=task_id,
                    rollback_error=str(rollback_error),
                )
            return False

    @staticmethod
    async def fail_task(
        db: AsyncSession, task_id: int, error: Exception, retry_eligible: bool = True
    ) -> bool:
        """Mark task as failed with error details."""

        try:
            failure_time = datetime.utcnow()

            # Get current retry count
            result = await db.execute(
                select(
                    Task.retry_count, Task.max_retries, Task.processing_started_at
                ).where(Task.id == task_id)
            )
            task_info = result.first()

            current_retries = task_info.retry_count if task_info else 0
            max_retries = task_info.max_retries if task_info else 3

            # Determine if we should retry or fail permanently
            should_retry = retry_eligible and current_retries < max_retries
            new_status = TaskStatus.PENDING if should_retry else TaskStatus.FAILED

            update_data = {
                "status": new_status,
                "error_message": str(error),
                "last_error_at": failure_time,
                "updated_at": failure_time,
                "retry_count": current_retries + 1,
            }

            # Add error details to progress details
            result = await db.execute(
                select(Task.progress_details).where(Task.id == task_id)
            )
            existing_details = result.scalar_one_or_none() or {}
            existing_details["last_error"] = {
                "message": str(error),
                "type": type(error).__name__,
                "timestamp": failure_time.isoformat(),
                "retry_count": current_retries + 1,
            }
            update_data["progress_details"] = existing_details

            # If permanently failed, set completion time
            if not should_retry:
                update_data["processing_completed_at"] = failure_time
                update_data["completed_at"] = failure_time

                # Calculate duration if we have start time
                if task_info and task_info.processing_started_at:
                    duration = int(
                        (failure_time - task_info.processing_started_at).total_seconds()
                    )
                    update_data["actual_duration_seconds"] = duration

            await db.execute(update(Task).where(Task.id == task_id).values(update_data))
            await db.commit()

            logger.error(
                "Task failed",
                task_id=task_id,
                error=str(error),
                retry_count=current_retries + 1,
                will_retry=should_retry,
            )
            return True

        except Exception as e:
            logger.error("Failed to mark task as failed", task_id=task_id, error=str(e))
            await db.rollback()
            return False

    @staticmethod
    async def get_task_status(
        db: AsyncSession, task_id: int, user_id: int | None = None
    ) -> dict[str, Any] | None:
        """Get comprehensive task status information."""

        try:
            query = select(Task).where(Task.id == task_id)
            if user_id is not None:
                query = query.where(Task.user_id == user_id)

            result = await db.execute(query)
            task = result.scalar_one_or_none()

            if not task:
                return None

            # Calculate estimated time remaining
            estimated_remaining = None
            if task.estimated_completion_at and task.status == TaskStatus.IN_PROGRESS:
                remaining = task.estimated_completion_at - datetime.utcnow()
                if remaining.total_seconds() > 0:
                    estimated_remaining = int(remaining.total_seconds())

            # Calculate elapsed time
            elapsed_seconds = None
            if task.processing_started_at:
                elapsed = datetime.utcnow() - task.processing_started_at
                elapsed_seconds = int(elapsed.total_seconds())

            return {
                "task_id": task.id,
                "status": task.status.value,
                "progress_percentage": task.progress_percentage or 0,
                "current_step": (
                    task.progress_details.get("current_step")
                    if task.progress_details
                    else None
                ),
                "worker_id": task.worker_id,
                "queue_name": task.queue_name,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "processing_started_at": (
                    task.processing_started_at.isoformat()
                    if task.processing_started_at
                    else None
                ),
                "estimated_completion_at": (
                    task.estimated_completion_at.isoformat()
                    if task.estimated_completion_at
                    else None
                ),
                "estimated_remaining_seconds": estimated_remaining,
                "elapsed_seconds": elapsed_seconds,
                "memory_usage_mb": task.memory_usage_mb,
                "browser_session_id": task.browser_session_id,
                "error_message": task.error_message,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "progress_details": task.progress_details or {},
                "result_data": (
                    task.result_data if task.status == TaskStatus.COMPLETED else None
                ),
            }

        except Exception as e:
            logger.error("Failed to get task status", task_id=task_id, error=str(e))
            return None

    @staticmethod
    async def get_active_tasks(
        db: AsyncSession, user_id: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get list of active (in-progress) tasks."""

        try:
            query = select(Task).where(Task.status == TaskStatus.IN_PROGRESS)
            if user_id is not None:
                query = query.where(Task.user_id == user_id)

            query = query.order_by(Task.processing_started_at.desc()).limit(limit)

            result = await db.execute(query)
            tasks = result.scalars().all()

            active_tasks = []
            for task in tasks:
                task_status = await TaskStatusService.get_task_status(db, task.id)
                if task_status:
                    active_tasks.append(task_status)

            return active_tasks

        except Exception as e:
            logger.error("Failed to get active tasks", error=str(e))
            return []

    @staticmethod
    async def cleanup_stale_tasks(db: AsyncSession, timeout_minutes: int = 30) -> int:
        """Cleanup tasks that have been processing too long."""

        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)

            # Find stale processing tasks
            result = await db.execute(
                select(Task).where(
                    Task.status == TaskStatus.IN_PROGRESS,
                    Task.processing_started_at < cutoff_time,
                )
            )
            stale_tasks = result.scalars().all()

            # Mark them as failed
            for task in stale_tasks:
                await TaskStatusService.fail_task(
                    db,
                    task.id,
                    Exception(f"Task timeout after {timeout_minutes} minutes"),
                    retry_eligible=True,
                )

            logger.info("Cleaned up stale tasks", count=len(stale_tasks))
            return len(stale_tasks)

        except Exception as e:
            logger.error("Failed to cleanup stale tasks", error=str(e))
            return 0

    @staticmethod
    async def get_task_metrics(
        db: AsyncSession, user_id: int | None = None, hours: int = 24
    ) -> dict[str, Any]:
        """Get task execution metrics for the specified time period."""

        try:
            since = datetime.utcnow() - timedelta(hours=hours)

            query = select(Task).where(Task.created_at >= since)
            if user_id is not None:
                query = query.where(Task.user_id == user_id)

            result = await db.execute(query)
            tasks = result.scalars().all()

            # Calculate metrics
            total_tasks = len(tasks)
            completed_tasks = len(
                [t for t in tasks if t.status == TaskStatus.COMPLETED]
            )
            failed_tasks = len([t for t in tasks if t.status == TaskStatus.FAILED])
            in_progress_tasks = len(
                [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
            )
            pending_tasks = len([t for t in tasks if t.status == TaskStatus.PENDING])

            # Calculate average duration for completed tasks
            completed_durations = [
                t.actual_duration_seconds
                for t in tasks
                if t.status == TaskStatus.COMPLETED and t.actual_duration_seconds
            ]
            avg_duration = (
                sum(completed_durations) / len(completed_durations)
                if completed_durations
                else 0
            )

            # Calculate success rate
            success_rate = (
                (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            )

            return {
                "period_hours": hours,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "pending_tasks": pending_tasks,
                "success_rate_percentage": round(success_rate, 2),
                "average_duration_seconds": round(avg_duration, 2),
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to get task metrics", error=str(e))
            return {"error": str(e), "generated_at": datetime.utcnow().isoformat()}
