import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeoutError

from app.core.config import settings
from app.core.logging import get_logger
from app.models.execution_plan import ExecutionPlan, AtomicAction, PlanStatus, ActionType, StepStatus
from app.models.task import Task, TaskStatus
from app.schemas.execution_plan import ExecutionPlan as ExecutionPlanSchema
from app.services.task_status_service import TaskStatusService
from app.utils.browser_pool import browser_pool
from app.executors.browser_actions import (
    ClickExecutor, TypeExecutor, NavigateExecutor, WaitExecutor,
    ScrollExecutor, SelectExecutor, SubmitExecutor, ScreenshotExecutor,
    HoverExecutor, KeyPressExecutor
)
from app.services.webhook_service import webhook_service

logger = get_logger(__name__)


class ExecutionResult:
    """Result of executing an ExecutionPlan."""
    
    def __init__(self, execution_id: str, plan_id: int):
        self.execution_id = execution_id
        self.plan_id = plan_id
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.status = "executing"
        self.current_step = 0
        self.total_steps = 0
        self.success = False
        self.error_message: Optional[str] = None
        self.executed_actions: List[Dict[str, Any]] = []
        self.screenshots: List[str] = []
        self.execution_logs: List[Dict[str, Any]] = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress_percentage": int((self.current_step / self.total_steps) * 100) if self.total_steps > 0 else 0,
            "success": self.success,
            "error_message": self.error_message,
            "executed_actions": len(self.executed_actions),
            "screenshots_captured": len(self.screenshots),
            "execution_duration_seconds": (
                (self.completed_at or datetime.utcnow()) - self.started_at
            ).total_seconds()
        }


class ActionExecutorService:
    """
    Phase 2D: ActionExecutor service that executes approved ExecutionPlans.
    
    This service takes approved plans from Phase 2C and executes them using
    browser automation, providing real-time progress tracking and comprehensive
    error handling.
    """
    
    def __init__(self):
        self.active_executions: Dict[str, ExecutionResult] = {}
        self.paused_executions: Dict[str, bool] = {}
        
        # Action executors
        self.action_executors = {
            ActionType.CLICK: ClickExecutor(),
            ActionType.TYPE: TypeExecutor(),
            ActionType.NAVIGATE: NavigateExecutor(),
            ActionType.WAIT: WaitExecutor(),
            ActionType.SCROLL: ScrollExecutor(),
            ActionType.SELECT: SelectExecutor(),
            ActionType.SUBMIT: SubmitExecutor(),
            ActionType.SCREENSHOT: ScreenshotExecutor(),
            ActionType.HOVER: HoverExecutor(),
            ActionType.KEY_PRESS: KeyPressExecutor(),
        }
        
        # Screenshot directory
        self.screenshot_dir = Path(settings.SCREENSHOT_DIR)
        self.screenshot_dir.mkdir(exist_ok=True)
        
        logger.info("ActionExecutor service initialized")
    
    async def execute_plan_async(
        self,
        db: AsyncSession,
        plan_id: int,
        user_id: int,
        execution_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute an approved ExecutionPlan asynchronously.
        
        Args:
            db: Database session
            plan_id: ID of the ExecutionPlan to execute
            user_id: ID of the user requesting execution
            execution_options: Optional execution configuration
            
        Returns:
            execution_id: Unique identifier for tracking this execution
        """
        execution_id = str(uuid.uuid4())
        execution_options = execution_options or {}
        
        try:
            # Validate plan exists and is approved
            plan = await self._get_and_validate_plan(db, plan_id, user_id)
            if not plan:
                raise ValueError(f"Plan {plan_id} not found or not approved for execution")
            
            # Create execution result tracker
            result = ExecutionResult(execution_id, plan_id)
            result.total_steps = len(plan.atomic_actions)
            self.active_executions[execution_id] = result
            
            # Update plan status to executing
            await self._update_plan_status(db, plan_id, PlanStatus.EXECUTING)
            
            # Start background execution
            asyncio.create_task(
                self._execute_plan_background(db, plan, execution_id, execution_options)
            )
            
            logger.info(
                "Plan execution started",
                execution_id=execution_id,
                plan_id=plan_id,
                user_id=user_id,
                total_steps=result.total_steps
            )
            
            return execution_id
            
        except Exception as e:
            logger.error(
                "Failed to start plan execution",
                plan_id=plan_id,
                user_id=user_id,
                error=str(e)
            )
            # Clean up if execution was created
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            raise
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an execution."""
        if execution_id not in self.active_executions:
            return None
        
        return self.active_executions[execution_id].to_dict()
    
    async def pause_execution(self, execution_id: str) -> bool:
        """Pause an active execution."""
        if execution_id not in self.active_executions:
            return False
        
        self.paused_executions[execution_id] = True
        self.active_executions[execution_id].status = "paused"
        
        logger.info("Execution paused", execution_id=execution_id)
        return True
    
    async def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution."""
        if execution_id not in self.active_executions:
            return False
        
        self.paused_executions[execution_id] = False
        self.active_executions[execution_id].status = "executing"
        
        logger.info("Execution resumed", execution_id=execution_id)
        return True
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution."""
        if execution_id not in self.active_executions:
            return False

        self.active_executions[execution_id].status = "cancelled"
        self.active_executions[execution_id].completed_at = datetime.utcnow()

        logger.info("Execution cancelled", execution_id=execution_id)
        return True

    async def _get_and_validate_plan(
        self,
        db: AsyncSession,
        plan_id: int,
        user_id: int
    ) -> Optional[ExecutionPlan]:
        """Get and validate that a plan is ready for execution."""
        try:
            result = await db.execute(
                select(ExecutionPlan)
                .where(
                    ExecutionPlan.id == plan_id,
                    ExecutionPlan.user_id == user_id,
                    ExecutionPlan.status == PlanStatus.APPROVED
                )
            )
            plan = result.scalar_one_or_none()

            if not plan:
                logger.warning(
                    "Plan not found or not approved",
                    plan_id=plan_id,
                    user_id=user_id
                )
                return None

            # Load atomic actions
            actions_result = await db.execute(
                select(AtomicAction)
                .where(AtomicAction.execution_plan_id == plan_id)
                .order_by(AtomicAction.step_number)
            )
            plan.atomic_actions = actions_result.scalars().all()

            return plan

        except Exception as e:
            logger.error(
                "Failed to get plan",
                plan_id=plan_id,
                user_id=user_id,
                error=str(e)
            )
            return None

    async def _update_plan_status(
        self,
        db: AsyncSession,
        plan_id: int,
        status: PlanStatus
    ) -> None:
        """Update plan status in database."""
        try:
            await db.execute(
                update(ExecutionPlan)
                .where(ExecutionPlan.id == plan_id)
                .values(
                    status=status,
                    updated_at=datetime.utcnow(),
                    started_at=datetime.utcnow() if status == PlanStatus.EXECUTING else None,
                    completed_at=datetime.utcnow() if status in [PlanStatus.COMPLETED, PlanStatus.FAILED] else None
                )
            )
            await db.commit()

        except Exception as e:
            logger.error(
                "Failed to update plan status",
                plan_id=plan_id,
                status=status,
                error=str(e)
            )
            await db.rollback()

    async def _execute_plan_background(
        self,
        db: AsyncSession,
        plan: ExecutionPlan,
        execution_id: str,
        execution_options: Dict[str, Any]
    ) -> None:
        """Execute the plan in the background."""
        result = self.active_executions[execution_id]
        context = None
        page = None

        try:
            # Initialize browser context
            if not browser_pool._initialized:
                await browser_pool.initialize()

            context = await browser_pool.acquire_context(f"execution-{execution_id}")
            page = await context.new_page()

            # Configure page for automation
            await self._configure_page_for_execution(page)

            # Navigate to starting URL if specified
            if plan.starting_url:
                await page.goto(plan.starting_url, wait_until="domcontentloaded")
                await self._take_screenshot(page, execution_id, "initial_page")

            # Execute each action step
            for action in plan.atomic_actions:
                # Check if execution is paused
                while self.paused_executions.get(execution_id, False):
                    await asyncio.sleep(1)

                # Check if execution was cancelled
                if result.status == "cancelled":
                    break

                # Monitor execution health before each step
                health_data = await self._monitor_execution_health(page, execution_id)
                result.execution_logs.append({
                    "type": "health_check",
                    "step_number": action.step_number,
                    "data": health_data,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Execute the action with retry logic
                success = False
                retry_count = 0
                max_retries = action.max_retries or 3

                while not success and retry_count <= max_retries:
                    try:
                        success = await self._execute_action(
                            db, page, action, execution_id, execution_options
                        )

                        if not success and retry_count < max_retries:
                            retry_count += 1
                            logger.info(
                                "Retrying action",
                                execution_id=execution_id,
                                step_number=action.step_number,
                                retry_count=retry_count,
                                max_retries=max_retries
                            )

                            # Wait before retry
                            await asyncio.sleep(action.retry_delay_seconds or 2)

                            # Update action retry count in database
                            await self._update_action_retry_count(db, action.id, retry_count)
                        else:
                            break

                    except Exception as e:
                        logger.error(
                            "Action execution error",
                            execution_id=execution_id,
                            step_number=action.step_number,
                            retry_count=retry_count,
                            error=str(e)
                        )
                        if retry_count >= max_retries:
                            break
                        retry_count += 1
                        await asyncio.sleep(action.retry_delay_seconds or 2)

                result.current_step = action.step_number

                # Handle critical step failure
                if not success and action.is_critical:
                    result.error_message = f"Critical step {action.step_number} failed: {action.description}"
                    logger.error(
                        "Critical step failed, aborting execution",
                        execution_id=execution_id,
                        step_number=action.step_number,
                        description=action.description
                    )
                    break

                # Log step completion
                result.execution_logs.append({
                    "type": "step_completed",
                    "step_number": action.step_number,
                    "success": success,
                    "retry_count": retry_count,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Send progress webhook notification
                await self._send_execution_progress_webhook(
                    plan.user_id, execution_id, plan.id,
                    action.step_number, result.total_steps
                )

            # Determine overall success
            result.success = (
                result.current_step == result.total_steps and
                result.status != "cancelled"
            )

            # Update final status and report results to planning system
            if result.status == "cancelled":
                final_status = PlanStatus.CANCELLED
            elif result.success:
                final_status = PlanStatus.COMPLETED
                result.status = "completed"
            else:
                final_status = PlanStatus.FAILED
                result.status = "failed"

            await self._update_plan_status(db, plan.id, final_status)

            # Report execution results back to planning system
            await self._report_execution_results_to_planning_system(
                db, plan, result, execution_id
            )

            # Send webhook notification for execution completion
            await self._send_execution_completion_webhook(
                plan.user_id, execution_id, plan.id, result
            )

        except Exception as e:
            logger.error(
                "Plan execution failed",
                execution_id=execution_id,
                plan_id=plan.id,
                error=str(e)
            )
            result.status = "failed"
            result.error_message = str(e)
            await self._update_plan_status(db, plan.id, PlanStatus.FAILED)

        finally:
            result.completed_at = datetime.utcnow()

            # Clean up browser resources
            if page:
                try:
                    await page.close()
                except:
                    pass

            if context:
                try:
                    await browser_pool.release_context(context, f"execution-{execution_id}")
                except:
                    pass

            logger.info(
                "Plan execution completed",
                execution_id=execution_id,
                plan_id=plan.id,
                success=result.success,
                steps_completed=result.current_step,
                total_steps=result.total_steps
            )


    async def _configure_page_for_execution(self, page: Page) -> None:
        """Configure page settings for reliable automation."""
        try:
            # Set viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})

            # Set user agent
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            # Disable images for faster loading (optional)
            if settings.DISABLE_IMAGES_FOR_EXECUTION:
                await page.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda route: route.abort())

        except Exception as e:
            logger.warning("Failed to configure page", error=str(e))

    async def _execute_action(
        self,
        db: AsyncSession,
        page: Page,
        action: AtomicAction,
        execution_id: str,
        execution_options: Dict[str, Any]
    ) -> bool:
        """Execute a single atomic action."""
        result = self.active_executions[execution_id]

        try:
            # Update action status to executing
            await self._update_action_status(db, action.id, StepStatus.EXECUTING)

            # Take before screenshot
            before_screenshot = await self._take_screenshot(
                page, execution_id, f"step_{action.step_number}_before"
            )

            # Log action start
            action_log = {
                "step_number": action.step_number,
                "action_type": action.action_type.value,
                "description": action.description,
                "started_at": datetime.utcnow().isoformat(),
                "target_selector": action.target_selector
            }
            result.execution_logs.append(action_log)

            # Get the appropriate executor
            executor = self.action_executors.get(action.action_type)
            if not executor:
                raise ValueError(f"No executor found for action type: {action.action_type}")

            # Execute the action with timeout
            success = await asyncio.wait_for(
                executor.execute(page, action),
                timeout=action.timeout_seconds
            )

            # Take after screenshot
            after_screenshot = await self._take_screenshot(
                page, execution_id, f"step_{action.step_number}_after"
            )

            # Validate action success if validation criteria provided
            if success and action.validation_criteria:
                validation_success = await self._validate_action_success(
                    page, action, execution_id
                )
                if not validation_success:
                    success = False
                    logger.warning(
                        "Action validation failed",
                        execution_id=execution_id,
                        step_number=action.step_number
                    )

            # Update action in database
            await self._update_action_result(
                db, action.id, success, None, before_screenshot, after_screenshot
            )

            # Update execution result
            action_result = {
                "step_number": action.step_number,
                "action_type": action.action_type.value,
                "success": success,
                "completed_at": datetime.utcnow().isoformat(),
                "before_screenshot": before_screenshot,
                "after_screenshot": after_screenshot
            }
            result.executed_actions.append(action_result)

            logger.info(
                "Action executed",
                execution_id=execution_id,
                step_number=action.step_number,
                action_type=action.action_type.value,
                success=success
            )

            return success

        except asyncio.TimeoutError:
            error_msg = f"Action timed out after {action.timeout_seconds} seconds"
            await self._handle_action_failure(db, action, error_msg, execution_id, page)
            return False

        except Exception as e:
            error_msg = f"Action failed: {str(e)}"
            await self._handle_action_failure(db, action, error_msg, execution_id, page)
            return False

    async def _update_action_status(
        self,
        db: AsyncSession,
        action_id: int,
        status: StepStatus
    ) -> None:
        """Update action status in database."""
        try:
            await db.execute(
                update(AtomicAction)
                .where(AtomicAction.id == action_id)
                .values(
                    status=status,
                    updated_at=datetime.utcnow(),
                    executed_at=datetime.utcnow() if status == StepStatus.EXECUTING else None,
                    completed_at=datetime.utcnow() if status in [StepStatus.COMPLETED, StepStatus.FAILED] else None
                )
            )
            await db.commit()

        except Exception as e:
            logger.error("Failed to update action status", action_id=action_id, error=str(e))
            await db.rollback()

    async def _update_action_result(
        self,
        db: AsyncSession,
        action_id: int,
        success: bool,
        error_message: Optional[str],
        before_screenshot: Optional[str],
        after_screenshot: Optional[str]
    ) -> None:
        """Update action execution result in database."""
        try:
            await db.execute(
                update(AtomicAction)
                .where(AtomicAction.id == action_id)
                .values(
                    status=StepStatus.COMPLETED if success else StepStatus.FAILED,
                    success=success,
                    error_message=error_message,
                    before_screenshot_path=before_screenshot,
                    after_screenshot_path=after_screenshot,
                    completed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()

        except Exception as e:
            logger.error("Failed to update action result", action_id=action_id, error=str(e))
            await db.rollback()

    async def _update_action_retry_count(
        self,
        db: AsyncSession,
        action_id: int,
        retry_count: int
    ) -> None:
        """Update action retry count in database."""
        try:
            await db.execute(
                update(AtomicAction)
                .where(AtomicAction.id == action_id)
                .values(
                    retry_count=retry_count,
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()

        except Exception as e:
            logger.error("Failed to update action retry count", action_id=action_id, error=str(e))
            await db.rollback()

    async def _handle_action_failure(
        self,
        db: AsyncSession,
        action: AtomicAction,
        error_message: str,
        execution_id: str,
        page: Optional[Page] = None
    ) -> None:
        """Handle action failure with comprehensive error logging and recovery."""
        result = self.active_executions[execution_id]

        # Capture error screenshot if page is available
        error_screenshot = None
        if page:
            error_screenshot = await self._take_screenshot(
                page, execution_id, f"step_{action.step_number}_error"
            )

        # Collect detailed error context
        error_context = {
            "error_message": error_message,
            "action_type": action.action_type.value,
            "target_selector": action.target_selector,
            "input_value": action.input_value,
            "timeout_seconds": action.timeout_seconds,
            "is_critical": action.is_critical,
            "retry_count": getattr(action, 'retry_count', 0),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add page context if available
        if page:
            try:
                error_context.update({
                    "page_url": page.url,
                    "page_title": await page.title(),
                    "viewport": page.viewport_size
                })
            except:
                pass

        # Update action as failed with detailed error info
        await self._update_action_result(
            db, action.id, False, error_message, None, error_screenshot
        )

        # Log comprehensive failure details
        failure_log = {
            "type": "action_failure",
            "step_number": action.step_number,
            "error_context": error_context,
            "recovery_attempted": False,
            "screenshot": error_screenshot
        }
        result.execution_logs.append(failure_log)

        # Attempt error recovery if possible
        recovery_success = await self._attempt_error_recovery(
            db, action, error_message, execution_id, page
        )

        if recovery_success:
            failure_log["recovery_attempted"] = True
            failure_log["recovery_success"] = True

        logger.error(
            "Action failed with detailed context",
            execution_id=execution_id,
            step_number=action.step_number,
            error_context=error_context,
            recovery_attempted=recovery_success
        )

    async def _attempt_error_recovery(
        self,
        db: AsyncSession,
        action: AtomicAction,
        error_message: str,
        execution_id: str,
        page: Optional[Page] = None
    ) -> bool:
        """Attempt to recover from action failure."""
        try:
            if not page:
                return False

            # Recovery strategy 1: Page refresh for stale element errors
            if "stale" in error_message.lower() or "detached" in error_message.lower():
                logger.info(f"Attempting page refresh recovery for step {action.step_number}")
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
                return True

            # Recovery strategy 2: Wait and retry for timeout errors
            if "timeout" in error_message.lower():
                logger.info(f"Attempting timeout recovery for step {action.step_number}")
                await asyncio.sleep(5)
                return True

            # Recovery strategy 3: Scroll to top for element not found errors
            if "not found" in error_message.lower():
                logger.info(f"Attempting scroll recovery for step {action.step_number}")
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1)
                return True

            return False

        except Exception as e:
            logger.warning(f"Error recovery attempt failed: {str(e)}")
            return False

    async def _take_screenshot(
        self,
        page: Page,
        execution_id: str,
        name: str
    ) -> Optional[str]:
        """Take a screenshot and return the file path."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{execution_id}_{name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename

            await page.screenshot(path=str(filepath), full_page=True)

            # Store relative path for database
            relative_path = f"screenshots/{filename}"

            logger.debug("Screenshot taken", filepath=relative_path)
            return relative_path

        except Exception as e:
            logger.warning("Failed to take screenshot", error=str(e))
            return None

    async def _validate_action_success(
        self,
        page: Page,
        action: AtomicAction,
        execution_id: str
    ) -> bool:
        """Validate that an action was successful based on validation criteria."""
        try:
            validation_criteria = action.validation_criteria or {}

            # Check for expected URL changes
            if "expected_url_contains" in validation_criteria:
                expected_url = validation_criteria["expected_url_contains"]
                current_url = page.url
                if expected_url not in current_url:
                    logger.warning(
                        "URL validation failed",
                        execution_id=execution_id,
                        expected=expected_url,
                        actual=current_url
                    )
                    return False

            # Check for expected elements to appear
            if "expected_element_visible" in validation_criteria:
                selector = validation_criteria["expected_element_visible"]
                try:
                    await page.wait_for_selector(selector, state="visible", timeout=5000)
                except PlaywrightTimeoutError:
                    logger.warning(
                        "Element visibility validation failed",
                        execution_id=execution_id,
                        selector=selector
                    )
                    return False

            # Check for expected text to appear
            if "expected_text_visible" in validation_criteria:
                text = validation_criteria["expected_text_visible"]
                try:
                    await page.wait_for_selector(f"text={text}", timeout=5000)
                except PlaywrightTimeoutError:
                    logger.warning(
                        "Text visibility validation failed",
                        execution_id=execution_id,
                        text=text
                    )
                    return False

            # Check for elements to disappear
            if "expected_element_hidden" in validation_criteria:
                selector = validation_criteria["expected_element_hidden"]
                try:
                    await page.wait_for_selector(selector, state="hidden", timeout=5000)
                except PlaywrightTimeoutError:
                    logger.warning(
                        "Element hidden validation failed",
                        execution_id=execution_id,
                        selector=selector
                    )
                    return False

            # Check for specific page state
            if "expected_page_state" in validation_criteria:
                state_check = validation_criteria["expected_page_state"]
                if state_check == "loaded":
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                elif state_check == "network_idle":
                    await page.wait_for_load_state("networkidle", timeout=10000)

            logger.info(
                "Action validation passed",
                execution_id=execution_id,
                step_number=action.step_number
            )
            return True

        except Exception as e:
            logger.error(
                "Action validation error",
                execution_id=execution_id,
                step_number=action.step_number,
                error=str(e)
            )
            return False

    async def _monitor_execution_health(
        self,
        page: Page,
        execution_id: str
    ) -> Dict[str, Any]:
        """Monitor execution health and performance metrics."""
        try:
            # Get page performance metrics
            metrics = await page.evaluate("""
                () => {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    return {
                        loadTime: navigation ? navigation.loadEventEnd - navigation.loadEventStart : 0,
                        domContentLoaded: navigation ? navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart : 0,
                        memoryUsage: performance.memory ? performance.memory.usedJSHeapSize : 0,
                        timestamp: Date.now()
                    };
                }
            """)

            # Get viewport and page info
            viewport = page.viewport_size
            url = page.url
            title = await page.title()

            health_data = {
                "execution_id": execution_id,
                "timestamp": datetime.utcnow().isoformat(),
                "page_url": url,
                "page_title": title,
                "viewport": viewport,
                "performance": metrics,
                "status": "healthy"
            }

            # Check for common issues
            if metrics.get("memoryUsage", 0) > 100 * 1024 * 1024:  # 100MB
                health_data["warnings"] = health_data.get("warnings", [])
                health_data["warnings"].append("High memory usage detected")

            return health_data

        except Exception as e:
            logger.warning(
                "Failed to collect execution health metrics",
                execution_id=execution_id,
                error=str(e)
            )
            return {
                "execution_id": execution_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "monitoring_error",
                "error": str(e)
            }

    async def get_execution_results(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed execution results after completion."""
        if execution_id not in self.active_executions:
            return None

        result = self.active_executions[execution_id]

        # Only return detailed results if execution is complete
        if result.status == "executing":
            return None

        # Calculate performance metrics
        performance_metrics = {
            "total_screenshots": len(result.screenshots),
            "total_execution_logs": len(result.execution_logs),
            "average_step_duration_ms": 0,
            "browser_memory_peak_mb": 0
        }

        if result.executed_actions:
            total_duration = sum(
                action.get("duration_ms", 0) for action in result.executed_actions
            )
            performance_metrics["average_step_duration_ms"] = (
                total_duration / len(result.executed_actions) if result.executed_actions else 0
            )

        # Convert executed actions to ActionResult format
        action_results = []
        for action_data in result.executed_actions:
            action_results.append({
                "step_number": action_data.get("step_number", 0),
                "action_type": action_data.get("action_type", "unknown"),
                "description": action_data.get("description", ""),
                "success": action_data.get("success", False),
                "started_at": action_data.get("started_at", ""),
                "completed_at": action_data.get("completed_at", ""),
                "duration_ms": action_data.get("duration_ms", 0),
                "error_message": action_data.get("error_message"),
                "before_screenshot": action_data.get("before_screenshot"),
                "after_screenshot": action_data.get("after_screenshot"),
                "target_selector": action_data.get("target_selector"),
                "input_value": action_data.get("input_value")
            })

        return {
            "execution_id": execution_id,
            "plan_id": result.plan_id,
            "status": result.status,
            "success": result.success,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "total_duration_seconds": (
                (result.completed_at or datetime.utcnow()) - result.started_at
            ).total_seconds(),
            "steps_completed": result.current_step,
            "total_steps": result.total_steps,
            "success_rate": (result.current_step / result.total_steps * 100) if result.total_steps > 0 else 0,
            "error_message": result.error_message,
            "action_results": action_results,
            "screenshots": result.screenshots,
            "performance_metrics": performance_metrics,
            "execution_logs": result.execution_logs
        }

    async def _report_execution_results_to_planning_system(
        self,
        db: AsyncSession,
        plan: ExecutionPlan,
        result: ExecutionResult,
        execution_id: str
    ) -> None:
        """Report execution results back to the planning system for learning."""
        try:
            # Calculate execution metrics
            success_rate = (result.current_step / result.total_steps) * 100 if result.total_steps > 0 else 0
            execution_duration = (
                (result.completed_at or datetime.utcnow()) - result.started_at
            ).total_seconds()

            # Update plan with execution results
            await db.execute(
                update(ExecutionPlan)
                .where(ExecutionPlan.id == plan.id)
                .values(
                    actual_success=result.success,
                    execution_success_rate=success_rate,
                    actual_duration_seconds=int(execution_duration),
                    execution_notes=f"Execution {execution_id}: {result.current_step}/{result.total_steps} steps completed",
                    updated_at=datetime.utcnow()
                )
            )

            await db.commit()

            logger.info(
                "Execution results reported to planning system",
                execution_id=execution_id,
                plan_id=plan.id,
                success_rate=success_rate,
                duration_seconds=execution_duration
            )

        except Exception as e:
            logger.error(
                "Failed to report execution results to planning system",
                execution_id=execution_id,
                plan_id=plan.id,
                error=str(e)
            )
            await db.rollback()

    async def _send_execution_completion_webhook(
        self,
        user_id: int,
        execution_id: str,
        plan_id: int,
        result: ExecutionResult
    ) -> None:
        """Send webhook notification for execution completion."""
        try:
            # Get detailed execution results for webhook
            execution_results = await self.get_execution_results(execution_id)

            if execution_results:
                await webhook_service.send_execution_completion_webhook(
                    user_id=user_id,
                    execution_id=execution_id,
                    plan_id=plan_id,
                    success=result.success,
                    execution_results=execution_results
                )

                logger.info(
                    "Execution completion webhook sent",
                    execution_id=execution_id,
                    plan_id=plan_id,
                    user_id=user_id,
                    success=result.success
                )

        except Exception as e:
            logger.error(
                "Failed to send execution completion webhook",
                execution_id=execution_id,
                plan_id=plan_id,
                user_id=user_id,
                error=str(e)
            )

    async def _send_execution_progress_webhook(
        self,
        user_id: int,
        execution_id: str,
        plan_id: int,
        current_step: int,
        total_steps: int
    ) -> None:
        """Send webhook notification for execution progress."""
        try:
            progress_percentage = int((current_step / total_steps) * 100) if total_steps > 0 else 0

            await webhook_service.send_execution_progress_webhook(
                user_id=user_id,
                execution_id=execution_id,
                plan_id=plan_id,
                current_step=current_step,
                total_steps=total_steps,
                progress_percentage=progress_percentage
            )

        except Exception as e:
            logger.warning(
                "Failed to send execution progress webhook",
                execution_id=execution_id,
                error=str(e)
            )


# Global service instance
action_executor_service = ActionExecutorService()
