"""
Task Service - CRUD operations and business logic for task management.

Provides comprehensive task management functionality including:
- Task creation, retrieval, updating, and deletion
- User permission validation
- Task filtering and pagination
- Task statistics and analytics
- Status management and validation
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskFilters, TaskStats, TaskList
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskService:
    """Service class for task management operations."""
    
    @staticmethod
    async def create_task(
        db: AsyncSession, 
        user_id: int, 
        task_data: TaskCreate
    ) -> Task:
        """
        Create a new task for the specified user.
        
        Args:
            db: Database session
            user_id: ID of the user creating the task
            task_data: Task creation data
            
        Returns:
            Created task instance
            
        Raises:
            ValueError: If task data is invalid
        """
        try:
            # Create task instance
            task = Task(
                user_id=user_id,
                title=task_data.title,
                description=task_data.description,
                goal=task_data.goal,
                target_url=str(task_data.target_url) if task_data.target_url else None,
                priority=task_data.priority,
                status=TaskStatus.PENDING,
                max_retries=task_data.max_retries,
                timeout_seconds=task_data.timeout_seconds,
                require_confirmation=task_data.require_confirmation,
                allow_sensitive_actions=task_data.allow_sensitive_actions,
                created_at=datetime.utcnow()
            )
            
            db.add(task)
            await db.commit()
            await db.refresh(task)
            
            logger.info("Task created successfully", 
                       task_id=task.id, user_id=user_id, title=task.title)
            
            return task
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create task", 
                        user_id=user_id, error=str(e))
            raise ValueError(f"Failed to create task: {str(e)}")
    
    @staticmethod
    async def get_task(
        db: AsyncSession, 
        task_id: int, 
        user_id: int
    ) -> Optional[Task]:
        """
        Get a specific task by ID, ensuring user ownership.
        
        Args:
            db: Database session
            task_id: ID of the task to retrieve
            user_id: ID of the user requesting the task
            
        Returns:
            Task instance if found and owned by user, None otherwise
        """
        try:
            query = select(Task).where(
                and_(Task.id == task_id, Task.user_id == user_id)
            ).options(
                selectinload(Task.execution_plan)
            )
            
            result = await db.execute(query)
            task = result.scalar_one_or_none()
            
            if task:
                logger.debug("Task retrieved successfully", 
                           task_id=task_id, user_id=user_id)
            else:
                logger.warning("Task not found or access denied", 
                             task_id=task_id, user_id=user_id)
            
            return task
            
        except Exception as e:
            logger.error("Failed to retrieve task", 
                        task_id=task_id, user_id=user_id, error=str(e))
            return None
    
    @staticmethod
    async def get_user_tasks(
        db: AsyncSession,
        user_id: int,
        filters: Optional[TaskFilters] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Task], int]:
        """
        Get paginated list of user's tasks with optional filtering.
        
        Args:
            db: Database session
            user_id: ID of the user
            filters: Optional filtering criteria
            page: Page number (1-based)
            page_size: Number of tasks per page
            
        Returns:
            Tuple of (tasks list, total count)
        """
        try:
            # Base query
            query = select(Task).where(Task.user_id == user_id)
            count_query = select(func.count(Task.id)).where(Task.user_id == user_id)
            
            # Apply filters
            if filters:
                conditions = []
                
                if filters.status:
                    conditions.append(Task.status == filters.status)
                
                if filters.priority:
                    conditions.append(Task.priority == filters.priority)
                
                if filters.created_after:
                    conditions.append(Task.created_at >= filters.created_after)
                
                if filters.created_before:
                    conditions.append(Task.created_at <= filters.created_before)
                
                if filters.domain:
                    conditions.append(Task.target_url.like(f"%{filters.domain}%"))
                
                if filters.search_query:
                    search_condition = or_(
                        Task.title.ilike(f"%{filters.search_query}%"),
                        Task.description.ilike(f"%{filters.search_query}%"),
                        Task.goal.ilike(f"%{filters.search_query}%")
                    )
                    conditions.append(search_condition)
                
                if conditions:
                    filter_condition = and_(*conditions)
                    query = query.where(filter_condition)
                    count_query = count_query.where(filter_condition)
            
            # Apply ordering (newest first)
            query = query.order_by(desc(Task.created_at))
            
            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # Execute queries
            tasks_result = await db.execute(query)
            tasks = tasks_result.scalars().all()
            
            count_result = await db.execute(count_query)
            total_count = count_result.scalar() or 0
            
            logger.debug("User tasks retrieved", 
                        user_id=user_id, count=len(tasks), total=total_count)
            
            return list(tasks), total_count
            
        except Exception as e:
            logger.error("Failed to retrieve user tasks", 
                        user_id=user_id, error=str(e))
            return [], 0
    
    @staticmethod
    async def update_task(
        db: AsyncSession,
        task_id: int,
        user_id: int,
        task_data: TaskUpdate
    ) -> Optional[Task]:
        """
        Update an existing task.
        
        Args:
            db: Database session
            task_id: ID of the task to update
            user_id: ID of the user updating the task
            task_data: Update data
            
        Returns:
            Updated task instance if successful, None otherwise
        """
        try:
            # Get existing task
            task = await TaskService.get_task(db, task_id, user_id)
            if not task:
                logger.warning("Task not found for update", 
                             task_id=task_id, user_id=user_id)
                return None
            
            # Check if task can be updated
            if task.status in [TaskStatus.IN_PROGRESS]:
                logger.warning("Cannot update task in progress", 
                             task_id=task_id, status=task.status)
                raise ValueError("Cannot update task while it's executing")
            
            # Apply updates
            update_data = task_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(task, field):
                    setattr(task, field, value)
            
            task.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(task)
            
            logger.info("Task updated successfully", 
                       task_id=task_id, user_id=user_id)
            
            return task
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update task", 
                        task_id=task_id, user_id=user_id, error=str(e))
            raise ValueError(f"Failed to update task: {str(e)}")
    
    @staticmethod
    async def delete_task(
        db: AsyncSession,
        task_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a task.
        
        Args:
            db: Database session
            task_id: ID of the task to delete
            user_id: ID of the user deleting the task
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Get existing task
            task = await TaskService.get_task(db, task_id, user_id)
            if not task:
                logger.warning("Task not found for deletion", 
                             task_id=task_id, user_id=user_id)
                return False
            
            # Check if task can be deleted
            if task.status == TaskStatus.IN_PROGRESS:
                logger.warning("Cannot delete task in progress", 
                             task_id=task_id, status=task.status)
                raise ValueError("Cannot delete task while it's executing")
            
            await db.delete(task)
            await db.commit()
            
            logger.info("Task deleted successfully", 
                       task_id=task_id, user_id=user_id)
            
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to delete task", 
                        task_id=task_id, user_id=user_id, error=str(e))
            raise ValueError(f"Failed to delete task: {str(e)}")
    
    @staticmethod
    async def get_task_stats(
        db: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> TaskStats:
        """
        Get task statistics for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            days: Number of days to include in statistics
            
        Returns:
            Task statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get basic counts
            total_query = select(func.count(Task.id)).where(
                and_(Task.user_id == user_id, Task.created_at >= cutoff_date)
            )
            total_tasks = (await db.execute(total_query)).scalar() or 0
            
            completed_query = select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.created_at >= cutoff_date
                )
            )
            completed_tasks = (await db.execute(completed_query)).scalar() or 0
            
            failed_query = select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.FAILED,
                    Task.created_at >= cutoff_date
                )
            )
            failed_tasks = (await db.execute(failed_query)).scalar() or 0
            
            pending_query = select(func.count(Task.id)).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.PENDING,
                    Task.created_at >= cutoff_date
                )
            )
            pending_tasks = (await db.execute(pending_query)).scalar() or 0
            
            # Calculate success rate
            success_rate = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0
            
            # Calculate average duration for completed tasks
            avg_duration_query = select(func.avg(Task.actual_duration_seconds)).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.actual_duration_seconds.isnot(None),
                    Task.created_at >= cutoff_date
                )
            )
            avg_duration = (await db.execute(avg_duration_query)).scalar()
            
            return TaskStats(
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                pending_tasks=pending_tasks,
                success_rate=success_rate,
                average_duration_seconds=avg_duration,
                most_common_domains=[],  # TODO: Implement domain analysis
                recent_activity=[]  # TODO: Implement recent activity
            )
            
        except Exception as e:
            logger.error("Failed to get task stats", 
                        user_id=user_id, error=str(e))
            return TaskStats(
                total_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                pending_tasks=0,
                success_rate=0.0
            )
