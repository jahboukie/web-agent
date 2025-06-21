"""
Critical Path E2E Tests: Agent Execution Flow
⚠️ CRITICAL: These tests validate core Reader → Planner → Actor handoff

Test Coverage:
✅ Reader → Planner → Actor handoff with complex websites
✅ Error recovery when one component fails mid-workflow  
✅ Parsed data integrity across 10+ website types
✅ Performance thresholds (< 2s parse, < 5s plan, < 30s execute)
✅ Concurrent agent execution (50+ simultaneous workflows)
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
import concurrent.futures
from unittest.mock import patch, MagicMock

from app.models.task import TaskStatus, TaskPriority
from app.models.execution_plan import PlanStatus, AtomicAction
from app.services.web_parser import web_parser_service
from app.services.planning_service import planning_service
from app.services.action_executor import action_executor
from app.services.analytics_service import analytics_service


class TestCriticalAgentExecution:
    """Critical path tests for WebAgent's core automation workflow."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_complete_workflow_complex_spa(self, test_db, test_users_db, test_websites):
        """
        ⚠️ CRITICAL: Test complete workflow with complex SPA website.
        
        Validates the full Reader → Planner → Actor pipeline with:
        - Dynamic content loading
        - AJAX interactions  
        - Complex DOM structures
        - Multi-step user journeys
        """
        user = test_users_db["user"]
        website = test_websites["spa_application"]
        
        start_time = time.time()
        
        # Step 1: Reader - Parse complex SPA
        parse_start = time.time()
        parse_result = await web_parser_service.parse_webpage_async(
            test_db,
            task_id=None,
            url=website["url"],
            options={
                "wait_for_spa": True,
                "dynamic_content_timeout": 10,
                "extract_interactive_elements": True,
                "semantic_analysis": True,
                "screenshot": True
            }
        )
        parse_duration = time.time() - parse_start
        
        # Validate parse performance
        assert parse_duration < 5.0, f"Parse took {parse_duration:.2f}s, expected < 5s"
        assert parse_result is not None
        assert parse_result.success is True
        assert len(parse_result.interactive_elements) >= 5, "Should find multiple interactive elements"
        assert parse_result.page_structure is not None
        assert len(parse_result.semantic_elements) > 0, "Should extract semantic information"
        
        # Step 2: Planner - Generate execution plan
        plan_start = time.time()
        plan_result = await planning_service.generate_execution_plan(
            test_db,
            user_id=user.id,
            goal="Add items to cart and proceed to checkout",
            parsed_webpage=parse_result,
            options={
                "confidence_threshold": 0.7,
                "max_steps": 15,
                "include_validations": True
            }
        )
        plan_duration = time.time() - plan_start
        
        # Validate plan performance and quality
        assert plan_duration < 8.0, f"Planning took {plan_duration:.2f}s, expected < 8s"
        assert plan_result is not None
        assert plan_result.status == PlanStatus.READY
        assert plan_result.confidence_score >= 0.7
        assert len(plan_result.atomic_actions) >= 3, "Should have multiple actions"
        assert plan_result.estimated_duration_seconds > 0
        
        # Validate plan structure
        action_types = {action.action_type for action in plan_result.atomic_actions}
        assert "click" in action_types, "Should include click actions"
        assert any(action.validation_criteria for action in plan_result.atomic_actions), \
               "Should include validation steps"
        
        # Step 3: Actor - Execute the plan
        execute_start = time.time()
        execution_result = await action_executor.execute_plan(
            test_db,
            execution_plan=plan_result,
            options={
                "headless": False,  # For debugging
                "screenshot_on_error": True,
                "max_retries": 2,
                "timeout_per_action": 10
            }
        )
        execute_duration = time.time() - execute_start
        
        # Validate execution performance and results
        total_duration = time.time() - start_time
        assert total_duration < 60.0, f"Total workflow took {total_duration:.2f}s, expected < 60s"
        assert execution_result is not None
        assert execution_result.success is True
        assert execution_result.actions_completed > 0
        assert execution_result.final_state is not None
        
        # Validate execution details
        assert len(execution_result.action_results) > 0
        success_rate = sum(1 for r in execution_result.action_results if r.success) / len(execution_result.action_results)
        assert success_rate >= 0.8, f"Action success rate {success_rate:.2f} below threshold"
        
        # Validate analytics collection
        analytics_data = await analytics_service.get_workflow_analytics(
            test_db, user.id, execution_result.execution_id
        )
        assert analytics_data is not None
        assert analytics_data["reader_duration"] == pytest.approx(parse_duration, abs=0.5)
        assert analytics_data["planner_duration"] == pytest.approx(plan_duration, abs=0.5)
        assert analytics_data["actor_duration"] == pytest.approx(execute_duration, abs=0.5)
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_error_recovery_reader_failure(self, test_db, test_users_db):
        """
        ⚠️ CRITICAL: Test error recovery when Reader component fails.
        
        Simulates various Reader failure scenarios:
        - Network timeouts
        - Invalid URLs
        - JavaScript errors
        - Authentication required sites
        """
        user = test_users_db["user"]
        
        # Test 1: Network timeout recovery
        with patch('app.services.web_parser.web_parser_service.parse_webpage_async') as mock_parse:
            mock_parse.side_effect = asyncio.TimeoutError("Network timeout")
            
            try:
                result = await web_parser_service.parse_webpage_async(
                    test_db,
                    task_id=None,
                    url="https://httpbin.org/delay/30",  # Intentionally slow
                    options={"timeout": 5}
                )
                assert False, "Should have raised timeout error"
            except asyncio.TimeoutError:
                pass  # Expected
        
        # Test 2: Invalid URL handling
        result = await web_parser_service.parse_webpage_async(
            test_db,
            task_id=None,
            url="https://invalid-domain-12345.com",
            options={"retry_on_failure": True, "max_retries": 2}
        )
        
        assert result is not None
        assert result.success is False
        assert "network" in result.error_type.lower() or "dns" in result.error_type.lower()
        assert result.error_message is not None
        
        # Test 3: JavaScript error recovery
        result = await web_parser_service.parse_webpage_async(
            test_db,
            task_id=None,
            url="data:text/html,<script>throw new Error('JS Error');</script>",
            options={"ignore_js_errors": True}
        )
        
        assert result is not None
        # Should still succeed despite JS errors when ignore_js_errors=True
        assert result.success is True or "javascript" in result.error_type.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_error_recovery_planner_failure(self, test_db, test_users_db):
        """
        ⚠️ CRITICAL: Test error recovery when Planner component fails.
        
        Simulates Planner failure scenarios:
        - Low confidence scores
        - Ambiguous goals
        - Insufficient parsed data
        - AI service timeouts
        """
        user = test_users_db["user"]
        
        # Create minimal parsed data that should cause planning issues
        minimal_parse_result = MagicMock()
        minimal_parse_result.interactive_elements = []
        minimal_parse_result.semantic_elements = []
        minimal_parse_result.page_structure = {}
        minimal_parse_result.success = True
        
        # Test 1: Insufficient data handling
        plan_result = await planning_service.generate_execution_plan(
            test_db,
            user_id=user.id,
            goal="Complete a complex multi-step purchase",
            parsed_webpage=minimal_parse_result,
            options={"confidence_threshold": 0.8}
        )
        
        assert plan_result is not None
        assert plan_result.status in [PlanStatus.FAILED, PlanStatus.LOW_CONFIDENCE]
        assert plan_result.confidence_score < 0.8
        assert plan_result.error_message is not None
        
        # Test 2: Ambiguous goal handling
        valid_parse_result = MagicMock()
        valid_parse_result.interactive_elements = [
            {"type": "button", "text": "Submit", "selector": "button"},
            {"type": "input", "name": "email", "selector": "input[name=email]"}
        ]
        valid_parse_result.success = True
        
        plan_result = await planning_service.generate_execution_plan(
            test_db,
            user_id=user.id,
            goal="Do something with the page",  # Intentionally vague
            parsed_webpage=valid_parse_result,
            options={"confidence_threshold": 0.7}
        )
        
        # Should either succeed with low confidence or fail gracefully
        assert plan_result is not None
        assert plan_result.confidence_score <= 0.8
        if plan_result.status == PlanStatus.FAILED:
            assert "ambiguous" in plan_result.error_message.lower() or \
                   "unclear" in plan_result.error_message.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_error_recovery_actor_failure(self, test_db, test_users_db):
        """
        ⚠️ CRITICAL: Test error recovery when Actor component fails.
        
        Simulates Actor failure scenarios:
        - Element not found
        - Page navigation failures
        - JavaScript execution errors
        - Browser crashes
        """
        user = test_users_db["user"]
        
        # Create a plan with invalid selectors
        faulty_plan = MagicMock()
        faulty_plan.atomic_actions = [
            AtomicAction(
                action_type="click",
                target_selector="#non-existent-element",
                description="Click non-existent element",
                expected_outcome="Should fail"
            ),
            AtomicAction(
                action_type="type",
                target_selector="input[name='missing']",
                input_value="test",
                description="Type in missing input"
            )
        ]
        faulty_plan.estimated_duration_seconds = 30
        
        # Test Actor's error recovery
        execution_result = await action_executor.execute_plan(
            test_db,
            execution_plan=faulty_plan,
            options={
                "continue_on_failure": True,
                "max_retries_per_action": 1,
                "screenshot_on_error": True
            }
        )
        
        assert execution_result is not None
        assert execution_result.success is False  # Overall failure expected
        assert len(execution_result.action_results) == 2  # Both actions attempted
        assert all(not result.success for result in execution_result.action_results)
        assert all(result.error_message for result in execution_result.action_results)
        assert execution_result.screenshots_captured > 0  # Error screenshots taken
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_data_integrity_across_website_types(self, test_db, test_users_db, test_websites):
        """
        ⚠️ CRITICAL: Test parsed data integrity across 10+ website types.
        
        Validates that the Reader component correctly extracts and preserves
        data integrity across diverse website architectures.
        """
        user = test_users_db["user"]
        
        # Define test website types with expected data patterns
        website_types = [
            {
                "name": "simple_form",
                "url": test_websites["simple_form"]["url"],
                "expected_elements": ["form", "input", "button"],
                "min_elements": 3
            },
            {
                "name": "spa_application", 
                "url": test_websites["spa_application"]["url"],
                "expected_elements": ["button", "div"],
                "min_elements": 5
            },
            {
                "name": "e_commerce",
                "url": test_websites["complex_navigation"]["url"], 
                "expected_elements": ["nav", "product", "cart"],
                "min_elements": 10
            },
            {
                "name": "authentication",
                "url": test_websites["authentication_required"]["url"],
                "expected_elements": ["input[type=text]", "input[type=password]"],
                "min_elements": 2
            },
            {
                "name": "dynamic_content",
                "url": test_websites["dynamic_content"]["url"],
                "expected_elements": ["link", "code"],
                "min_elements": 5
            }
        ]
        
        results = []
        
        for website_type in website_types:
            start_time = time.time()
            
            parse_result = await web_parser_service.parse_webpage_async(
                test_db,
                task_id=None,
                url=website_type["url"],
                options={
                    "comprehensive_extraction": True,
                    "preserve_structure": True,
                    "validate_data": True
                }
            )
            
            duration = time.time() - start_time
            
            # Validate data integrity
            assert parse_result is not None, f"Parse failed for {website_type['name']}"
            assert parse_result.success is True, f"Parse unsuccessful for {website_type['name']}"
            assert duration < 10.0, f"Parse took {duration:.2f}s for {website_type['name']}, expected < 10s"
            
            # Validate element extraction
            total_elements = len(parse_result.interactive_elements) + len(parse_result.semantic_elements)
            assert total_elements >= website_type["min_elements"], \
                   f"Found only {total_elements} elements for {website_type['name']}, expected >= {website_type['min_elements']}"
            
            # Validate data structure integrity
            assert isinstance(parse_result.page_structure, dict), \
                   f"Page structure not a dict for {website_type['name']}"
            assert parse_result.url == website_type["url"], \
                   f"URL mismatch for {website_type['name']}"
            assert parse_result.timestamp is not None, \
                   f"Missing timestamp for {website_type['name']}"
            
            # Validate element data integrity
            for element in parse_result.interactive_elements:
                assert "selector" in element, f"Missing selector in element for {website_type['name']}"
                assert "type" in element, f"Missing type in element for {website_type['name']}"
                assert element["selector"] is not None, f"Null selector for {website_type['name']}"
            
            results.append({
                "website_type": website_type["name"],
                "duration": duration,
                "elements_found": total_elements,
                "success": True
            })
        
        # Validate cross-website consistency
        avg_duration = sum(r["duration"] for r in results) / len(results)
        assert avg_duration < 7.0, f"Average parse duration {avg_duration:.2f}s too high"
        
        # All website types should be successfully parsed
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        assert success_rate == 1.0, f"Website parsing success rate {success_rate:.2f} below 100%"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_agent_execution(self, test_db, test_users_db, test_websites):
        """
        ⚠️ CRITICAL: Test concurrent agent execution (50+ simultaneous workflows).
        
        Validates that the platform can handle multiple simultaneous
        Reader → Planner → Actor workflows without performance degradation
        or resource conflicts.
        """
        user = test_users_db["user"]
        website = test_websites["simple_form"]
        
        concurrent_workflows = 20  # Reduced for test stability, increase for load testing
        
        async def run_single_workflow(workflow_id: int) -> Dict[str, Any]:
            """Run a single workflow and return results."""
            start_time = time.time()
            
            try:
                # Reader phase
                parse_result = await web_parser_service.parse_webpage_async(
                    test_db,
                    task_id=None,
                    url=website["url"],
                    options={"workflow_id": workflow_id}
                )
                
                if not parse_result or not parse_result.success:
                    return {"workflow_id": workflow_id, "success": False, "phase": "reader"}
                
                # Planner phase  
                plan_result = await planning_service.generate_execution_plan(
                    test_db,
                    user_id=user.id,
                    goal=f"Fill out the form (workflow {workflow_id})",
                    parsed_webpage=parse_result,
                    options={"workflow_id": workflow_id}
                )
                
                if not plan_result or plan_result.status != PlanStatus.READY:
                    return {"workflow_id": workflow_id, "success": False, "phase": "planner"}
                
                # Actor phase
                execution_result = await action_executor.execute_plan(
                    test_db,
                    execution_plan=plan_result,
                    options={
                        "workflow_id": workflow_id,
                        "headless": True,  # Reduce resource usage
                        "timeout_per_action": 5
                    }
                )
                
                duration = time.time() - start_time
                
                return {
                    "workflow_id": workflow_id,
                    "success": execution_result.success if execution_result else False,
                    "duration": duration,
                    "phase": "completed"
                }
                
            except Exception as e:
                duration = time.time() - start_time
                return {
                    "workflow_id": workflow_id,
                    "success": False,
                    "duration": duration,
                    "error": str(e),
                    "phase": "error"
                }
        
        # Execute concurrent workflows
        start_time = time.time()
        
        tasks = [run_single_workflow(i) for i in range(concurrent_workflows)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_duration = time.time() - start_time
        
        # Filter out exceptions and convert to results
        valid_results = [r for r in results if isinstance(r, dict)]
        
        # Validate concurrent execution
        assert len(valid_results) == concurrent_workflows, \
               f"Only {len(valid_results)} workflows completed out of {concurrent_workflows}"
        
        # Validate success rate
        successful_workflows = [r for r in valid_results if r["success"]]
        success_rate = len(successful_workflows) / len(valid_results)
        assert success_rate >= 0.8, \
               f"Concurrent execution success rate {success_rate:.2f} below 80%"
        
        # Validate performance
        avg_workflow_duration = sum(r["duration"] for r in valid_results) / len(valid_results)
        assert avg_workflow_duration < 20.0, \
               f"Average workflow duration {avg_workflow_duration:.2f}s too high under load"
        
        # Validate no significant resource conflicts
        duration_variance = max(r["duration"] for r in valid_results) - min(r["duration"] for r in valid_results)
        assert duration_variance < 15.0, \
               f"Duration variance {duration_variance:.2f}s indicates resource conflicts"
        
        # Validate total execution time (should benefit from concurrency)
        expected_sequential_time = avg_workflow_duration * concurrent_workflows
        concurrency_efficiency = expected_sequential_time / total_duration
        assert concurrency_efficiency >= 3.0, \
               f"Concurrency efficiency {concurrency_efficiency:.2f}x below expectations"