"""
E2E Tests: Agent Execution Flow (Reader → Planner → Actor)
Critical path testing for WebAgent's core automation workflow
"""

import asyncio
from datetime import datetime

import pytest

from app.models.execution_plan import PlanStatus
from app.models.task import TaskStatus
from app.services.action_executor import action_executor
from app.services.planning_service import planning_service
from app.services.web_parser import web_parser_service


class TestAgentExecutionFlow:
    """Test the complete Reader → Planner → Actor workflow."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_workflow_simple_form(
        self, test_db, test_users_db, test_websites
    ):
        """
        Test complete workflow with simple form website.

        Flow: Parse webpage → Generate plan → Execute actions
        Expected: Successful completion with valid results
        """
        user = test_users_db["user"]
        website = test_websites["simple_form"]

        # Step 1: Reader - Parse webpage
        parse_result = await web_parser_service.parse_webpage_async(
            test_db,
            task_id=None,  # Will create internal task
            url=website["url"],
            options={
                "extract_forms": True,
                "extract_links": True,
                "semantic_analysis": True,
                "wait_for_load": 3,
            },
        )

        assert parse_result is not None
        assert parse_result.success is True
        assert len(parse_result.interactive_elements) > 0

        # Verify expected elements are found
        element_types = [
            elem.element_type for elem in parse_result.interactive_elements
        ]
        for expected_type in website["expected_elements"]:
            assert any(
                expected_type in elem_type for elem_type in element_types
            ), f"Expected element type '{expected_type}' not found"

        # Step 2: Planner - Generate execution plan
        planning_result = await planning_service.generate_plan_async(
            test_db,
            task_id=parse_result.task_id,
            user_goal="Fill out and submit the form with test data",
            planning_options={
                "planning_timeout_seconds": 120,
                "max_agent_iterations": 10,
                "planning_temperature": 0.1,
            },
            user_id=user.id,
        )

        assert planning_result is not None
        assert planning_result.status == PlanStatus.APPROVED
        assert planning_result.total_actions > 0
        assert planning_result.confidence_score > 0.7

        # Step 3: Actor - Execute the plan
        execution_id = await action_executor.execute_plan_async(
            test_db,
            plan_id=planning_result.id,
            user_id=user.id,
            execution_options={
                "take_screenshots": True,
                "screenshot_frequency": 2,
                "execution_timeout_seconds": 300,
            },
        )

        assert execution_id is not None

        # Wait for execution to complete (with timeout)
        max_wait = 300  # 5 minutes
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < max_wait:
            execution_result = action_executor.get_execution_status(execution_id)

            if execution_result.status in ["completed", "failed"]:
                break

            await asyncio.sleep(2)

        # Verify execution completed successfully
        final_result = action_executor.get_execution_status(execution_id)
        assert final_result.status == "completed"
        assert final_result.success_rate > 0.8
        assert len(final_result.screenshots) > 0

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_with_spa_application(
        self, test_db, test_users_db, test_websites
    ):
        """
        Test workflow with complex SPA application.

        Validates handling of dynamic content and JavaScript-heavy sites.
        """
        user = test_users_db["manager"]
        website = test_websites["spa_application"]

        # Parse SPA with extended wait times
        parse_result = await web_parser_service.parse_webpage_async(
            test_db,
            task_id=None,
            url=website["url"],
            options={
                "wait_for_load": 10,  # Longer wait for SPA
                "wait_for_network_idle": True,
                "extract_forms": True,
                "extract_links": True,
                "semantic_analysis": True,
                "has_spa_content": True,
            },
        )

        assert parse_result is not None
        assert parse_result.success is True

        # SPA should have more complex structure
        assert parse_result.complexity_score > 0.6
        assert len(parse_result.interactive_elements) >= 5

        # Generate plan for SPA interaction
        planning_result = await planning_service.generate_plan_async(
            test_db,
            task_id=parse_result.task_id,
            user_goal="Navigate through the shopping cart application and add items",
            planning_options={
                "planning_timeout_seconds": 180,  # More time for complex planning
                "max_agent_iterations": 15,
                "planning_temperature": 0.2,
            },
            user_id=user.id,
        )

        assert planning_result is not None
        assert planning_result.total_actions >= 3  # Should have multiple steps
        assert planning_result.complexity_score > 0.5

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_recovery_mid_workflow(
        self, test_db, test_users_db, test_websites
    ):
        """
        Test error recovery when components fail mid-workflow.

        Simulates failures and validates graceful recovery.
        """
        user = test_users_db["user"]
        website = test_websites["simple_form"]

        # Start with successful parsing
        parse_result = await web_parser_service.parse_webpage_async(
            test_db, task_id=None, url=website["url"], options={"extract_forms": True}
        )

        assert parse_result.success is True

        # Simulate planning failure with invalid parameters
        with pytest.raises(Exception):
            await planning_service.generate_plan_async(
                test_db,
                task_id=parse_result.task_id,
                user_goal="",  # Empty goal should cause failure
                planning_options={"planning_timeout_seconds": 1},  # Too short timeout
                user_id=user.id,
            )

        # Verify task status reflects the failure
        from app.services.task_service import TaskService

        task = await TaskService.get_task(test_db, parse_result.task_id, user.id)
        assert task.status == TaskStatus.FAILED
        assert task.error_message is not None

        # Test recovery with valid parameters
        recovery_result = await planning_service.generate_plan_async(
            test_db,
            task_id=parse_result.task_id,
            user_goal="Fill out the form with test data",
            planning_options={
                "planning_timeout_seconds": 120,
                "max_agent_iterations": 10,
            },
            user_id=user.id,
        )

        assert recovery_result is not None
        assert recovery_result.status == PlanStatus.APPROVED

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_data_integrity_across_components(
        self, test_db, test_users_db, test_websites
    ):
        """
        Test data integrity as information flows between components.

        Validates that parsed data is correctly used in planning and execution.
        """
        user = test_users_db["user"]
        website = test_websites["authentication_required"]

        # Parse authentication page
        parse_result = await web_parser_service.parse_webpage_async(
            test_db,
            task_id=None,
            url=website["url"],
            options={"extract_forms": True, "semantic_analysis": True},
        )

        # Verify specific form elements are captured
        form_elements = [
            elem
            for elem in parse_result.interactive_elements
            if elem.element_type in ["input", "button"]
        ]
        assert len(form_elements) >= 3  # Username, password, submit

        # Check that form data includes required attributes
        username_field = next(
            (elem for elem in form_elements if "username" in elem.selector.lower()),
            None,
        )
        password_field = next(
            (elem for elem in form_elements if "password" in elem.selector.lower()),
            None,
        )

        assert username_field is not None
        assert password_field is not None

        # Generate plan and verify it references the correct elements
        planning_result = await planning_service.generate_plan_async(
            test_db,
            task_id=parse_result.task_id,
            user_goal="Log in with username 'tomsmith' and password 'SuperSecretPassword!'",
            planning_options={
                "planning_timeout_seconds": 120,
                "max_agent_iterations": 10,
            },
            user_id=user.id,
        )

        # Verify plan includes actions for the identified form elements
        action_selectors = [
            action.selector for action in planning_result.atomic_actions
        ]

        # Should have actions targeting the username and password fields
        assert any(username_field.selector in selector for selector in action_selectors)
        assert any(password_field.selector in selector for selector in action_selectors)

        # Verify action parameters include the specified credentials
        type_actions = [
            action
            for action in planning_result.atomic_actions
            if action.action_type.value == "TYPE"
        ]

        action_values = [action.parameters.get("text", "") for action in type_actions]
        assert "tomsmith" in str(action_values)
        assert "SuperSecretPassword!" in str(action_values)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_workflow_performance_benchmarks(
        self, test_db, test_users_db, test_websites
    ):
        """
        Test workflow performance against benchmarks.

        Validates that each component meets performance requirements.
        """
        user = test_users_db["user"]
        website = test_websites["simple_form"]

        # Benchmark parsing performance
        parse_start = datetime.utcnow()
        parse_result = await web_parser_service.parse_webpage_async(
            test_db, task_id=None, url=website["url"], options={"extract_forms": True}
        )
        parse_duration = (datetime.utcnow() - parse_start).total_seconds()

        # Parsing should complete within 30 seconds for simple sites
        assert parse_duration < 30
        assert parse_result.parsing_duration_ms < 30000

        # Benchmark planning performance
        plan_start = datetime.utcnow()
        planning_result = await planning_service.generate_plan_async(
            test_db,
            task_id=parse_result.task_id,
            user_goal="Fill out the form",
            planning_options={
                "planning_timeout_seconds": 60,
                "max_agent_iterations": 8,
            },
            user_id=user.id,
        )
        plan_duration = (datetime.utcnow() - plan_start).total_seconds()

        # Planning should complete within 60 seconds
        assert plan_duration < 60

        # Verify plan quality metrics
        assert planning_result.confidence_score > 0.6
        assert planning_result.total_actions <= 10  # Should be efficient

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_workflow_execution(
        self, test_db, test_users_db, test_websites
    ):
        """
        Test multiple workflows running concurrently.

        Validates system stability under concurrent load.
        """
        users = [test_users_db["user"], test_users_db["manager"]]
        websites = [test_websites["simple_form"], test_websites["spa_application"]]

        # Create concurrent parsing tasks
        parse_tasks = []
        for i, (user, website) in enumerate(zip(users, websites, strict=False)):
            task = web_parser_service.parse_webpage_async(
                test_db,
                task_id=None,
                url=website["url"],
                options={"extract_forms": True},
            )
            parse_tasks.append(task)

        # Execute concurrently
        parse_results = await asyncio.gather(*parse_tasks, return_exceptions=True)

        # Verify all parsing completed successfully
        for result in parse_results:
            assert not isinstance(result, Exception)
            assert result.success is True

        # Create concurrent planning tasks
        plan_tasks = []
        for i, (user, result) in enumerate(zip(users, parse_results, strict=False)):
            task = planning_service.generate_plan_async(
                test_db,
                task_id=result.task_id,
                user_goal=f"Complete task {i+1}",
                planning_options={"planning_timeout_seconds": 90},
                user_id=user.id,
            )
            plan_tasks.append(task)

        # Execute planning concurrently
        plan_results = await asyncio.gather(*plan_tasks, return_exceptions=True)

        # Verify all planning completed successfully
        for result in plan_results:
            assert not isinstance(result, Exception)
            assert result.status == PlanStatus.APPROVED
