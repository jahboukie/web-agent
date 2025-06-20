from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog
import json
import asyncio
from datetime import datetime, timedelta

from app.models.execution_plan import ExecutionPlan, AtomicAction, PlanStatus, ActionType, StepStatus
from app.models.task import Task
from app.services.task_status_service import TaskStatusService
from app.langchain.agents.planning_agent import PlanningAgent
from app.langchain.tools.webpage_tools import WebpageAnalysisTool, ElementInspectorTool, ActionCapabilityAssessor
from app.langchain.validation.plan_validator import PlanValidator
from app.langchain.memory.planning_memory import PlanningMemory

logger = structlog.get_logger(__name__)


class PlanningService:
    """
    Phase 2C: Core service for AI-powered execution plan generation using LangChain ReAct agents.
    
    This service orchestrates the entire planning process:
    1. Retrieves parsed webpage data from completed tasks
    2. Initializes LangChain agent with custom tools and memory
    3. Executes planning workflow with ReAct reasoning
    4. Validates generated plans for safety and feasibility
    5. Stores structured plans in database with metadata
    """
    
    def __init__(self):
        """Initialize planning service with LangChain components."""
        self.planning_agent = None
        self.plan_validator = PlanValidator()
        self.planning_memory = PlanningMemory()
        self.confidence_threshold = 0.75
        self.max_planning_time = 300  # 5 minutes
        self._initialized = False
    
    async def initialize(self):
        """Initialize LangChain agent and supporting components."""
        if self._initialized:
            return
        
        try:
            # Initialize planning agent
            self.planning_agent = PlanningAgent()
            await self.planning_agent.initialize()
            
            # Initialize planning memory
            await self.planning_memory.initialize()
            
            self._initialized = True
            logger.info("Planning service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize planning service", error=str(e))
            raise
    
    async def generate_plan_async(
        self,
        db: AsyncSession,
        task_id: int,
        user_goal: str,
        planning_options: Dict[str, Any],
        user_id: int
    ) -> ExecutionPlan:
        """
        Generate execution plan using LangChain ReAct agent.
        
        Process:
        1. Mark task as in progress with planning status
        2. Retrieve and validate parsed webpage data
        3. Initialize agent with webpage context and tools
        4. Execute ReAct planning workflow
        5. Parse agent output into structured ExecutionPlan
        6. Validate plan for safety and feasibility
        7. Store plan in database with all metadata
        8. Update task status with completion or failure
        
        Args:
            db: Database session
            task_id: ID of the planning task
            user_goal: Natural language goal from user
            planning_options: Configuration options for planning
            user_id: User requesting the plan
            
        Returns:
            Generated ExecutionPlan with all action steps
        """
        
        # Ensure service is initialized
        if not self._initialized:
            await self.initialize()
        
        # Mark task as processing
        await TaskStatusService.mark_task_processing(db, task_id, "planning_service")
        
        try:
            # Update progress: Retrieving source data
            await TaskStatusService.update_task_progress(
                db, task_id, 10, "retrieving_source_data"
            )
            
            # Get source task and webpage data
            source_task, webpage_data = await self._get_source_data(db, task_id, user_id)
            
            # Update progress: Initializing AI agent
            await TaskStatusService.update_task_progress(
                db, task_id, 20, "initializing_ai_agent"
            )
            
            # Prepare agent context
            agent_context = await self._prepare_agent_context(
                webpage_data, user_goal, planning_options
            )
            
            # Update progress: Generating plan with AI
            await TaskStatusService.update_task_progress(
                db, task_id, 30, "generating_plan_with_ai"
            )
            
            # Execute planning with ReAct agent
            planning_start_time = datetime.utcnow()
            agent_result = await self._execute_planning_workflow(
                agent_context, planning_options
            )
            planning_duration_ms = int((datetime.utcnow() - planning_start_time).total_seconds() * 1000)
            
            # Update progress: Parsing agent output
            await TaskStatusService.update_task_progress(
                db, task_id, 60, "parsing_agent_output"
            )
            
            # Parse agent output into structured plan
            execution_plan = await self._parse_agent_output(
                db, task_id, user_id, source_task, agent_result, planning_duration_ms, planning_options
            )
            
            # Update progress: Validating plan
            await TaskStatusService.update_task_progress(
                db, task_id, 80, "validating_plan"
            )
            
            # Validate generated plan
            validation_result = await self.validate_plan(execution_plan)
            execution_plan.validation_passed = validation_result['is_valid']
            execution_plan.validation_warnings = validation_result.get('warnings', [])
            execution_plan.validation_errors = validation_result.get('errors', [])
            execution_plan.plan_quality_score = validation_result.get('confidence_score', 0.0)
            
            # Update progress: Finalizing plan
            await TaskStatusService.update_task_progress(
                db, task_id, 90, "finalizing_plan"
            )
            
            # Determine plan status based on validation and requirements
            if execution_plan.requires_approval or not validation_result['is_valid']:
                execution_plan.status = PlanStatus.PENDING_APPROVAL
            else:
                execution_plan.status = PlanStatus.APPROVED
            
            # Save plan to database
            await db.commit()
            
            # Complete task with plan results
            plan_summary = {
                "execution_plan_id": execution_plan.id,
                "total_steps": execution_plan.total_actions,
                "overall_confidence": execution_plan.confidence_score,
                "complexity_level": execution_plan.complexity_level,
                "requires_approval": execution_plan.requires_approval,
                "validation_passed": execution_plan.validation_passed,
                "planning_duration_ms": planning_duration_ms,
                "agent_iterations": execution_plan.agent_iterations,
                "tokens_used": execution_plan.planning_tokens_used
            }
            
            await TaskStatusService.complete_task(db, task_id, plan_summary)
            
            logger.info(
                "AI plan generation completed successfully",
                task_id=task_id,
                plan_id=execution_plan.id,
                total_steps=execution_plan.total_actions,
                confidence=execution_plan.confidence_score,
                duration_ms=planning_duration_ms
            )
            
            return execution_plan
            
        except Exception as e:
            logger.error("AI plan generation failed", task_id=task_id, error=str(e))
            await TaskStatusService.fail_task(db, task_id, e)
            raise
    
    async def _get_source_data(self, db: AsyncSession, task_id: int, user_id: int) -> tuple:
        """Retrieve and validate source task with webpage data."""
        
        # Get the planning task
        result = await db.execute(
            select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        planning_task = result.scalar_one_or_none()
        
        if not planning_task:
            raise ValueError(f"Planning task {task_id} not found")
        
        # Find the source parsing task (most recent completed task for this user)
        result = await db.execute(
            select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.status == "completed",
                    Task.result_data.isnot(None)
                )
            ).order_by(Task.completed_at.desc()).limit(1)
        )
        source_task = result.scalar_one_or_none()
        
        if not source_task or not source_task.result_data:
            raise ValueError("No completed webpage parsing task found with results")
        
        # Extract webpage data from source task
        webpage_data = source_task.result_data.get('result_data', {})
        if not webpage_data or 'web_page' not in webpage_data:
            raise ValueError("Source task does not contain valid webpage parsing results")
        
        return source_task, webpage_data
    
    async def _prepare_agent_context(
        self,
        webpage_data: Dict[str, Any],
        user_goal: str,
        planning_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for LangChain agent execution."""
        
        # Extract key webpage information
        web_page = webpage_data.get('web_page', {})
        interactive_elements = webpage_data.get('interactive_elements', [])
        content_blocks = webpage_data.get('content_blocks', [])
        
        # Create agent context
        context = {
            'user_goal': user_goal,
            'webpage_url': web_page.get('url'),
            'webpage_title': web_page.get('title'),
            'webpage_domain': web_page.get('domain'),
            'interactive_elements': interactive_elements,
            'content_blocks': content_blocks,
            'total_elements': len(interactive_elements),
            'planning_options': planning_options,
            'webpage_summary': self._create_webpage_summary(web_page, interactive_elements, content_blocks)
        }
        
        return context
    
    def _create_webpage_summary(
        self,
        web_page: Dict[str, Any],
        interactive_elements: List[Dict[str, Any]],
        content_blocks: List[Dict[str, Any]]
    ) -> str:
        """Create concise webpage summary for agent context."""
        
        summary_parts = [
            f"URL: {web_page.get('url', 'unknown')}",
            f"Title: {web_page.get('title', 'unknown')}",
            f"Interactive Elements: {len(interactive_elements)}",
            f"Content Blocks: {len(content_blocks)}"
        ]
        
        # Add element type summary
        element_types = {}
        for element in interactive_elements:
            element_type = element.get('element_type', 'unknown')
            element_types[element_type] = element_types.get(element_type, 0) + 1
        
        if element_types:
            element_summary = ", ".join([f"{count} {type}" for type, count in element_types.items()])
            summary_parts.append(f"Element Types: {element_summary}")
        
        return " | ".join(summary_parts)
    
    async def _execute_planning_workflow(
        self,
        agent_context: Dict[str, Any],
        planning_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute LangChain ReAct agent planning workflow."""
        
        try:
            # Create tools for this specific webpage
            tools = [
                WebpageAnalysisTool(webpage_data=agent_context),
                ElementInspectorTool(webpage_data=agent_context),
                ActionCapabilityAssessor(webpage_data=agent_context)
            ]
            
            # Execute agent with timeout
            planning_timeout = planning_options.get('planning_timeout_seconds', 300)
            
            agent_result = await asyncio.wait_for(
                self.planning_agent.execute_planning(
                    goal=agent_context['user_goal'],
                    context=agent_context,
                    tools=tools,
                    temperature=planning_options.get('planning_temperature', 0.1),
                    max_iterations=planning_options.get('max_agent_iterations', 15)
                ),
                timeout=planning_timeout
            )
            
            return agent_result
            
        except asyncio.TimeoutError:
            raise ValueError(f"Planning timeout after {planning_timeout} seconds")
        except Exception as e:
            logger.error("Agent execution failed", error=str(e))
            raise ValueError(f"Agent planning failed: {str(e)}")
    
    async def _parse_agent_output(
        self,
        db: AsyncSession,
        task_id: int,
        user_id: int,
        source_task: Task,
        agent_result: Dict[str, Any],
        planning_duration_ms: int,
        planning_options: Dict[str, Any]
    ) -> ExecutionPlan:
        """Parse LangChain agent output into structured ExecutionPlan."""
        
        try:
            # Extract plan data from agent result
            plan_data = agent_result.get('execution_plan', {})
            action_steps = agent_result.get('action_steps', [])
            
            if not plan_data or not action_steps:
                raise ValueError("Agent did not generate valid execution plan")
            
            # Create ExecutionPlan
            execution_plan = ExecutionPlan(
                task_id=task_id,
                user_id=user_id,
                title=plan_data.get('title', f"Execute: {source_task.goal[:100]}"),
                description=plan_data.get('description'),
                original_goal=source_task.goal,
                source_webpage_url=source_task.target_url,
                source_webpage_data=source_task.result_data.get('result_data', {}),
                
                # Plan content
                total_actions=len(action_steps),
                estimated_duration_seconds=plan_data.get('estimated_duration_seconds', 60),
                confidence_score=plan_data.get('confidence_score', 0.5),
                complexity_score=plan_data.get('complexity_score', 0.5),
                
                # AI metadata
                llm_model_used=agent_result.get('llm_model', 'claude-3-5-sonnet-20241022'),
                agent_iterations=agent_result.get('iterations_used', 0),
                planning_tokens_used=agent_result.get('tokens_used', 0),
                planning_duration_ms=planning_duration_ms,
                planning_temperature=planning_options.get('planning_temperature', 0.1),
                
                # Classification
                automation_category=plan_data.get('automation_category', 'general'),
                requires_sensitive_actions=plan_data.get('requires_sensitive_actions', False),
                complexity_level=plan_data.get('complexity_level', 'medium'),
                
                # Approval workflow
                requires_approval=planning_options.get('require_user_approval', True),
                
                # Risk assessment
                risk_assessment=plan_data.get('risk_assessment', {}),
                
                # Learning
                learning_tags=plan_data.get('learning_tags', []),
                
                status=PlanStatus.DRAFT
            )
            
            db.add(execution_plan)
            await db.flush()  # Get the ID
            
            # Create action steps
            for i, step_data in enumerate(action_steps, 1):
                atomic_action = AtomicAction(
                    execution_plan_id=execution_plan.id,
                    
                    # Step identification
                    step_number=i,
                    step_name=step_data.get('step_name', f"Step {i}"),
                    description=step_data.get('description', ''),
                    
                    # Action definition
                    action_type=ActionType(step_data.get('action_type', 'click')),
                    target_selector=step_data.get('target_selector'),
                    input_value=step_data.get('input_value'),
                    action_data=step_data.get('action_data', {}),
                    
                    # Element targeting
                    element_xpath=step_data.get('element_xpath'),
                    element_css_selector=step_data.get('element_css_selector'),
                    element_attributes=step_data.get('element_attributes', {}),
                    element_text_content=step_data.get('element_text_content'),
                    
                    # Confidence and validation
                    confidence_score=step_data.get('confidence_score', 0.5),
                    expected_outcome=step_data.get('expected_outcome'),
                    validation_criteria=step_data.get('validation_criteria', {}),
                    
                    # Error handling
                    fallback_actions=step_data.get('fallback_actions', []),
                    timeout_seconds=step_data.get('timeout_seconds', 30),
                    max_retries=step_data.get('max_retries', 3),
                    
                    # Dependencies
                    depends_on_steps=step_data.get('depends_on_steps', []),
                    conditional_logic=step_data.get('conditional_logic', {}),
                    
                    # Metadata
                    is_critical=step_data.get('is_critical', False),
                    requires_confirmation=step_data.get('requires_confirmation', False),
                    
                    status=StepStatus.PENDING
                )
                
                db.add(atomic_action)
            
            return execution_plan
            
        except Exception as e:
            logger.error("Failed to parse agent output", error=str(e))
            raise ValueError(f"Failed to parse agent output: {str(e)}")
    
    async def validate_plan(self, execution_plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Validate execution plan for safety, feasibility, and quality.
        
        Validation includes:
        - Element selector reliability
        - Action sequence logic
        - Safety constraint compliance
        - Confidence score calibration
        """
        
        try:
            # Use plan validator to check all aspects
            validation_result = await self.plan_validator.validate_plan(execution_plan)
            
            return validation_result
            
        except Exception as e:
            logger.error("Plan validation failed", plan_id=execution_plan.id, error=str(e))
            return {
                'is_valid': False,
                'confidence_score': 0.0,
                'warnings': [],
                'errors': [f"Validation failed: {str(e)}"],
                'element_validation': {},
                'sequence_validation': {},
                'safety_validation': {},
                'recommendations': ['Review plan manually before execution']
            }
    
    async def get_planning_metrics(
        self,
        db: AsyncSession,
        user_id: int,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get planning metrics and analytics for the specified time period."""
        
        try:
            # Calculate time range
            since_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get execution plans in time range
            result = await db.execute(
                select(ExecutionPlan).where(
                    and_(
                        ExecutionPlan.user_id == user_id,
                        ExecutionPlan.created_at >= since_time
                    )
                )
            )
            plans = result.scalars().all()
            
            if not plans:
                return self._empty_metrics()
            
            # Calculate metrics
            total_plans = len(plans)
            approved_plans = len([p for p in plans if p.approved_by_user])
            
            avg_confidence = sum(p.confidence_score for p in plans) / total_plans
            avg_generation_time = sum(p.planning_duration_ms or 0 for p in plans) / total_plans
            avg_steps = sum(p.total_actions for p in plans) / total_plans
            avg_tokens = sum(p.planning_tokens_used or 0 for p in plans) / total_plans
            
            # Category distribution
            categories = {}
            complexities = {}
            for plan in plans:
                cat = plan.automation_category or 'unknown'
                categories[cat] = categories.get(cat, 0) + 1
                
                comp = plan.complexity_level or 'medium'
                complexities[comp] = complexities.get(comp, 0) + 1
            
            return {
                'total_plans_generated': total_plans,
                'average_confidence': round(avg_confidence, 3),
                'success_rate': 1.0,  # TODO: Calculate from execution results
                'average_generation_time_ms': int(avg_generation_time),
                'category_distribution': categories,
                'complexity_distribution': complexities,
                'approval_rate': round(approved_plans / total_plans, 3) if total_plans > 0 else 0.0,
                'user_satisfaction': 4.5,  # TODO: Calculate from user ratings
                'average_steps_per_plan': round(avg_steps, 1),
                'average_tokens_per_plan': int(avg_tokens)
            }
            
        except Exception as e:
            logger.error("Failed to calculate planning metrics", error=str(e))
            return self._empty_metrics()
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'total_plans_generated': 0,
            'average_confidence': 0.0,
            'success_rate': 0.0,
            'average_generation_time_ms': 0,
            'category_distribution': {},
            'complexity_distribution': {},
            'approval_rate': 0.0,
            'user_satisfaction': 0.0,
            'average_steps_per_plan': 0.0,
            'average_tokens_per_plan': 0
        }


# Global planning service instance
planning_service = PlanningService()