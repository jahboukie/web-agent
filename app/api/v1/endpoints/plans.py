from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog

from app.schemas.planning import (
    PlanGenerationRequest, PlanGenerationResponse, PlanStatusResponse,
    PlanApprovalRequest, PlanApprovalResponse, ExecutionPlanSchema,
    PlanValidationResult, PlanMetrics, PlanTemplateSchema
)
from app.schemas.user import User
from app.models.execution_plan import ExecutionPlan, AtomicAction, PlanStatus, PlanTemplate
from app.models.task import Task, TaskStatus
from app.db.session import get_async_session
from app.api.dependencies import get_current_user
from app.services.planning_service import PlanningService
from app.services.task_status_service import TaskStatusService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize planning service
planning_service = PlanningService()


async def _process_plan_generation_async(
    task_id: int,
    user_goal: str,
    planning_options: Dict[str, Any],
    user_id: int
):
    """Async background task function for AI plan generation."""
    
    logger.info("🧠 AI PLAN GENERATION STARTED", task_id=task_id, user_goal=user_goal[:100])
    
    # Get database session
    async for db in get_async_session():
        try:
            # Generate execution plan using LangChain ReAct agent
            execution_plan = await planning_service.generate_plan_async(
                db, task_id, user_goal, planning_options, user_id
            )
            
            logger.info(
                "✅ AI plan generation completed",
                task_id=task_id,
                plan_id=execution_plan.id,
                total_steps=execution_plan.total_actions,
                confidence=execution_plan.confidence_score
            )
            
        except Exception as e:
            logger.error("❌ AI plan generation failed", task_id=task_id, error=str(e))
            
            # Update task status to failed
            await TaskStatusService.fail_task(db, task_id, e)
        
        # Always break after first iteration since we only need one session
        break


def _process_plan_generation(
    task_id: int,
    user_goal: str,
    planning_options: Dict[str, Any],
    user_id: int
):
    """Sync wrapper for background plan generation (required by FastAPI BackgroundTasks)."""
    
    logger.info("🎯 PLAN GENERATION SYNC WRAPPER", task_id=task_id, user_goal=user_goal[:50])
    
    import asyncio
    
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function
        loop.run_until_complete(
            _process_plan_generation_async(task_id, user_goal, planning_options, user_id)
        )
        
        logger.info("🎉 PLAN GENERATION BACKGROUND TASK COMPLETED", task_id=task_id)
        
    except Exception as e:
        logger.error("💥 PLAN GENERATION BACKGROUND TASK FAILED", task_id=task_id, error=str(e))


@router.post("/generate", response_model=PlanGenerationResponse)
async def generate_execution_plan(
    plan_request: PlanGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Generate an AI-powered execution plan for a user goal.
    
    This endpoint creates a background task that uses a LangChain ReAct agent
    to analyze parsed webpage data and generate a structured execution plan.
    
    Process:
    1. Validates that source task exists and is completed
    2. Creates planning task record
    3. Queues background AI plan generation
    4. Returns immediately with task tracking information
    
    Returns:
    - plan_id: Unique identifier for generated plan
    - status: Planning status (always "generating" initially)  
    - estimated_completion: When planning will be done
    """
    
    try:
        # Validate source task exists and is completed
        result = await db.execute(
            select(Task).where(
                and_(
                    Task.id == plan_request.task_id,
                    Task.user_id == current_user.id,
                    Task.status == TaskStatus.COMPLETED
                )
            )
        )
        source_task = result.scalar_one_or_none()
        
        if not source_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source task not found or not completed"
            )
        
        # Verify source task has webpage parsing results
        if not source_task.result_data or 'web_page' not in source_task.result_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source task does not contain webpage parsing results"
            )
        
        # Create planning task record
        planning_task = Task(
            user_id=current_user.id,
            title=f"Generate execution plan: {plan_request.user_goal[:100]}",
            description=f"AI-powered plan generation for goal: {plan_request.user_goal}",
            goal=plan_request.user_goal,
            target_url=source_task.target_url,
            priority=source_task.priority,
            status=TaskStatus.PENDING,
            user_goal=plan_request.user_goal,
            planning_status="generating",
            max_retries=1,  # Plan generation typically doesn't need retries
            timeout_seconds=plan_request.planning_options.planning_timeout_seconds,
            require_confirmation=False,
            allow_sensitive_actions=plan_request.planning_options.allow_sensitive_actions
        )
        
        db.add(planning_task)
        await db.commit()
        await db.refresh(planning_task)
        
        # Queue background AI plan generation
        background_tasks.add_task(
            _process_plan_generation,
            task_id=planning_task.id,
            user_goal=plan_request.user_goal,
            planning_options=plan_request.planning_options.model_dump(),
            user_id=current_user.id
        )
        
        logger.info(
            "AI plan generation queued",
            task_id=planning_task.id,
            source_task_id=plan_request.task_id,
            user_goal=plan_request.user_goal[:100],
            user_id=current_user.id
        )
        
        # Return immediately with task information
        return PlanGenerationResponse(
            plan_id=planning_task.id,
            status="generating",
            message="AI plan generation started - analyzing webpage and creating execution plan",
            estimated_completion_seconds=plan_request.planning_options.planning_timeout_seconds,
            check_status_url=f"/api/v1/plans/{planning_task.id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to queue AI plan generation", error=str(e), task_id=plan_request.task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start AI plan generation: {str(e)}"
        )


@router.get("/{plan_id}", response_model=PlanStatusResponse)
async def get_plan_status(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get execution plan details and current generation/execution status.
    
    Returns real-time status information including:
    - Current generation progress
    - Plan summary (when available)
    - Quality metrics and confidence scores
    - Approval workflow status
    """
    
    try:
        # Get planning task status
        task_status = await TaskStatusService.get_task_status(db, plan_id, current_user.id)
        
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found or access denied"
            )
        
        # Get execution plan if available
        result = await db.execute(
            select(ExecutionPlan).where(
                and_(
                    ExecutionPlan.task_id == plan_id,
                    ExecutionPlan.user_id == current_user.id
                )
            )
        )
        execution_plan = result.scalar_one_or_none()
        
        # Build response based on current status
        response_data = {
            "plan_id": plan_id,
            "status": PlanStatus.GENERATING if task_status['status'] == 'in_progress' else PlanStatus.DRAFT,
            "progress_percentage": task_status.get('progress_percentage', 0),
            "current_step": task_status.get('current_step', 'initializing'),
            "message": _get_status_message(task_status, execution_plan)
        }
        
        # Add plan details if available
        if execution_plan:
            response_data.update({
                "status": execution_plan.status,
                "total_steps": execution_plan.total_actions,
                "overall_confidence": execution_plan.confidence_score,
                "complexity_level": execution_plan.complexity_level,
                "requires_approval": execution_plan.requires_approval,
                "generation_duration_ms": execution_plan.planning_duration_ms,
                "agent_iterations": execution_plan.agent_iterations,
                "tokens_used": execution_plan.planning_tokens_used
            })
        
        return PlanStatusResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get plan status", plan_id=plan_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan status"
        )


@router.get("/{plan_id}/details", response_model=ExecutionPlanSchema)
async def get_plan_details(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get complete execution plan details including all action steps.
    
    Returns the full plan structure with:
    - All action steps with confidence scores
    - Element selectors and validation criteria
    - Risk assessment and safety considerations
    - Human approval workflow status
    """
    
    try:
        # Get execution plan with action steps
        result = await db.execute(
            select(ExecutionPlan).where(
                and_(
                    ExecutionPlan.task_id == plan_id,
                    ExecutionPlan.user_id == current_user.id
                )
            )
        )
        execution_plan = result.scalar_one_or_none()
        
        if not execution_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution plan not found or not yet generated"
            )
        
        # Convert to schema with action steps
        return ExecutionPlanSchema.model_validate(execution_plan)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get plan details", plan_id=plan_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan details"
        )


@router.post("/{plan_id}/approve", response_model=PlanApprovalResponse)
async def approve_execution_plan(
    plan_id: int,
    approval_request: PlanApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Approve, reject, or request modifications to a generated execution plan.
    
    Human-in-the-loop workflow for plan quality assurance:
    - Review generated plan steps and confidence scores
    - Approve for immediate execution
    - Reject with feedback for improvement
    - Request specific modifications
    
    Returns updated plan status and next steps.
    """
    
    try:
        # Get execution plan
        result = await db.execute(
            select(ExecutionPlan).where(
                and_(
                    ExecutionPlan.task_id == plan_id,
                    ExecutionPlan.user_id == current_user.id
                )
            )
        )
        execution_plan = result.scalar_one_or_none()
        
        if not execution_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution plan not found"
            )
        
        if execution_plan.status != PlanStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan is not pending approval. Current status: {execution_plan.status}"
            )
        
        # Process approval decision
        if approval_request.approval_decision == "approve":
            execution_plan.status = PlanStatus.APPROVED
            execution_plan.approved_by_user = True
            execution_plan.approved_at = func.now()
            execution_plan.approval_feedback = approval_request.feedback
            
            # Override confidence if provided
            if approval_request.confidence_override:
                execution_plan.confidence_score = approval_request.confidence_override
            
            message = "Plan approved and ready for execution"
            next_action_url = f"/api/v1/plans/{plan_id}/execute"
            
        elif approval_request.approval_decision == "reject":
            execution_plan.status = PlanStatus.REJECTED
            execution_plan.approval_feedback = approval_request.feedback
            
            message = "Plan rejected - feedback recorded for improvement"
            next_action_url = f"/api/v1/plans/generate"  # Generate new plan
            
        elif approval_request.approval_decision == "modify":
            # Handle modification requests (future enhancement)
            execution_plan.status = PlanStatus.DRAFT
            execution_plan.approval_feedback = approval_request.feedback
            
            message = "Modification requested - plan returned to draft status"
            next_action_url = f"/api/v1/plans/{plan_id}/modify"
        
        await db.commit()
        
        logger.info(
            "Plan approval processed",
            plan_id=plan_id,
            decision=approval_request.approval_decision,
            user_id=current_user.id
        )
        
        return PlanApprovalResponse(
            plan_id=plan_id,
            status=execution_plan.status,
            ready_for_execution=(execution_plan.status == PlanStatus.APPROVED),
            message=message,
            next_action_url=next_action_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process plan approval", plan_id=plan_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process plan approval"
        )


@router.post("/{plan_id}/validate", response_model=PlanValidationResult)
async def validate_execution_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Validate execution plan for safety, feasibility, and quality.
    
    Comprehensive validation including:
    - Element selector reliability
    - Action sequence logic
    - Safety constraint compliance
    - Confidence score calibration
    
    Returns detailed validation results and recommendations.
    """
    
    try:
        # Get execution plan
        result = await db.execute(
            select(ExecutionPlan).where(
                and_(
                    ExecutionPlan.task_id == plan_id,
                    ExecutionPlan.user_id == current_user.id
                )
            )
        )
        execution_plan = result.scalar_one_or_none()
        
        if not execution_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution plan not found"
            )
        
        # Perform validation using planning service
        validation_result = await planning_service.validate_plan(execution_plan)
        
        # Update plan validation status
        execution_plan.validation_passed = validation_result['is_valid']
        execution_plan.validation_warnings = validation_result['warnings']
        execution_plan.validation_errors = validation_result['errors']
        execution_plan.plan_quality_score = validation_result['confidence_score']
        
        await db.commit()
        
        logger.info(
            "Plan validation completed",
            plan_id=plan_id,
            is_valid=validation_result['is_valid'],
            confidence=validation_result['confidence_score']
        )
        
        return PlanValidationResult(**validation_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to validate plan", plan_id=plan_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate execution plan"
        )


@router.get("/metrics", response_model=PlanMetrics)
async def get_planning_metrics(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get planning metrics and analytics for the specified time period.
    
    Returns statistics about:
    - Plan generation performance
    - Success rates and quality metrics
    - User satisfaction and approval rates
    - Resource usage (tokens, time, iterations)
    """
    
    try:
        metrics = await planning_service.get_planning_metrics(db, current_user.id, hours)
        return PlanMetrics(**metrics)
        
    except Exception as e:
        logger.error("Failed to get planning metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve planning metrics"
        )


@router.get("/templates", response_model=List[PlanTemplateSchema])
async def get_plan_templates(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get available plan templates for common automation patterns.
    
    Templates accelerate planning by providing proven patterns for:
    - Form submissions
    - Navigation workflows
    - File operations
    - E-commerce interactions
    """
    
    try:
        query = select(PlanTemplate)
        if category:
            query = query.where(PlanTemplate.category == category)
        
        result = await db.execute(query.order_by(PlanTemplate.usage_count.desc()))
        templates = result.scalars().all()
        
        return [PlanTemplateSchema.model_validate(template) for template in templates]
        
    except Exception as e:
        logger.error("Failed to get plan templates", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan templates"
        )


def _get_status_message(task_status: Dict[str, Any], execution_plan: Optional[ExecutionPlan]) -> str:
    """Generate appropriate status message based on current state."""
    
    if task_status['status'] == 'completed' and execution_plan:
        if execution_plan.requires_approval:
            return f"Plan generated with {execution_plan.total_actions} steps (confidence: {execution_plan.confidence_score:.1%}) - awaiting approval"
        else:
            return f"Plan generated and ready for execution - {execution_plan.total_actions} steps with {execution_plan.confidence_score:.1%} confidence"
    elif task_status['status'] == 'failed':
        return f"Plan generation failed: {task_status.get('error_message', 'Unknown error')}"
    elif task_status['status'] == 'in_progress':
        return f"Generating plan: {task_status.get('current_step', 'Processing...')}"
    else:
        return "Plan generation queued"