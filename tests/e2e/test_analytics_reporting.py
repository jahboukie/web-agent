"""
E2E Tests: Analytics & Reporting Validation
Validate dashboard metrics, upgrade CTAs, ROI calculator, billing integration, and audit log exports
"""

import asyncio
import csv
import io
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.analytics_service import analytics_service
from app.services.billing_service import billing_service
from app.services.subscription_service import subscription_service


class TestDashboardMetrics:
    """Test dashboard metrics accuracy and real-time updates."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_real_time_usage_counters(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test real-time usage counters vs backend metrics.

        Validates that dashboard counters accurately reflect actual usage.
        """
        user = test_users_db["user"]

        # Set user to specific subscription tier with known limits
        await subscription_service.update_user_subscription(
            test_db,
            user.id,
            {
                "tier": "reader_pro",
                "limits": {"parses": 2000, "plans": 200, "executions": 100},
                "usage": {"parses_used": 0, "plans_used": 0, "executions_used": 0},
            },
        )

        # Get initial dashboard metrics
        response = test_client.get(
            "/api/v1/analytics/dashboard", headers=auth_headers["user"]
        )
        assert response.status_code == 200
        initial_metrics = response.json()

        # Verify initial state
        assert initial_metrics["subscription"]["usage"]["parses_used"] == 0
        assert initial_metrics["subscription"]["usage"]["plans_used"] == 0
        assert initial_metrics["subscription"]["usage"]["executions_used"] == 0

        # Perform activities that should increment counters
        activities = [
            {
                "action": "parse_webpage",
                "endpoint": "/api/v1/web-pages/parse",
                "payload": {
                    "url": "https://httpbin.org/forms/post",
                    "force_refresh": False,
                },
                "expected_increment": {"parses_used": 1},
            },
            {
                "action": "generate_plan",
                "endpoint": "/api/v1/plans/generate",
                "payload": {
                    "task_id": 1,  # Will be updated with actual task ID
                    "user_goal": "Fill out the form",
                    "planning_options": {"planning_timeout_seconds": 60},
                },
                "expected_increment": {"plans_used": 1},
            },
        ]

        # Create a task first for plan generation
        task_response = test_client.post(
            "/api/v1/tasks/",
            json={
                "title": "Test Task for Analytics",
                "description": "Task for testing analytics",
                "goal": "Test analytics tracking",
            },
            headers=auth_headers["user"],
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]

        # Update plan generation payload with actual task ID
        activities[1]["payload"]["task_id"] = task_id

        # Execute activities and verify metrics update
        for activity in activities:
            # Perform the activity
            if activity["action"] == "parse_webpage":
                response = test_client.post(
                    activity["endpoint"],
                    json=activity["payload"],
                    headers=auth_headers["user"],
                )
            elif activity["action"] == "generate_plan":
                response = test_client.post(
                    activity["endpoint"],
                    json=activity["payload"],
                    headers=auth_headers["user"],
                )

            # Activity should succeed
            assert response.status_code in [
                200,
                201,
                202,
            ], f"Activity {activity['action']} failed with status {response.status_code}"

            # Wait for metrics to update (allow for async processing)
            await asyncio.sleep(2)

            # Get updated dashboard metrics
            metrics_response = test_client.get(
                "/api/v1/analytics/dashboard", headers=auth_headers["user"]
            )
            assert metrics_response.status_code == 200
            updated_metrics = metrics_response.json()

            # Verify counters incremented correctly
            for metric_name, expected_increment in activity[
                "expected_increment"
            ].items():
                initial_value = initial_metrics["subscription"]["usage"][metric_name]
                updated_value = updated_metrics["subscription"]["usage"][metric_name]

                assert updated_value == initial_value + expected_increment, (
                    f"Metric {metric_name} not incremented correctly: "
                    f"expected {initial_value + expected_increment}, got {updated_value}"
                )

            # Update initial metrics for next iteration
            initial_metrics = updated_metrics

        # Verify percentage calculations are accurate
        final_metrics = updated_metrics["subscription"]

        for usage_type in ["parses", "plans", "executions"]:
            used_key = f"{usage_type}_used"
            limit_key = usage_type
            percentage_key = f"{usage_type}_percentage"

            if (
                used_key in final_metrics["usage"]
                and limit_key in final_metrics["limits"]
            ):
                used = final_metrics["usage"][used_key]
                limit = final_metrics["limits"][limit_key]
                expected_percentage = (used / limit) * 100 if limit > 0 else 0

                if "usage_percentages" in final_metrics:
                    actual_percentage = final_metrics["usage_percentages"].get(
                        percentage_key, 0
                    )
                    assert abs(actual_percentage - expected_percentage) < 0.1, (
                        f"Percentage calculation incorrect for {usage_type}: "
                        f"expected {expected_percentage:.1f}%, got {actual_percentage:.1f}%"
                    )

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_upgrade_cta_accuracy(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test upgrade CTAs at 80%/95%/100% usage.

        Validates that upgrade prompts appear at correct usage thresholds.
        """
        user = test_users_db["user"]

        # Test scenarios with different usage levels
        usage_scenarios = [
            {
                "name": "Low usage (50%)",
                "usage": {"parses_used": 100, "plans_used": 10, "executions_used": 5},
                "limits": {"parses": 200, "plans": 20, "executions": 10},
                "expected_cta": False,
            },
            {
                "name": "High usage (80%)",
                "usage": {"parses_used": 160, "plans_used": 16, "executions_used": 8},
                "limits": {"parses": 200, "plans": 20, "executions": 10},
                "expected_cta": True,
                "cta_type": "warning",
            },
            {
                "name": "Critical usage (95%)",
                "usage": {"parses_used": 190, "plans_used": 19, "executions_used": 9},
                "limits": {"parses": 200, "plans": 20, "executions": 10},
                "expected_cta": True,
                "cta_type": "urgent",
            },
            {
                "name": "Limit reached (100%)",
                "usage": {"parses_used": 200, "plans_used": 20, "executions_used": 10},
                "limits": {"parses": 200, "plans": 20, "executions": 10},
                "expected_cta": True,
                "cta_type": "blocked",
            },
        ]

        for scenario in usage_scenarios:
            # Set user subscription to scenario values
            await subscription_service.update_user_subscription(
                test_db,
                user.id,
                {
                    "tier": "free",
                    "limits": scenario["limits"],
                    "usage": scenario["usage"],
                },
            )

            # Get dashboard with current usage
            response = test_client.get(
                "/api/v1/analytics/dashboard", headers=auth_headers["user"]
            )
            assert response.status_code == 200
            dashboard_data = response.json()

            # Check upgrade CTA presence and type
            if scenario["expected_cta"]:
                assert (
                    "upgrade_cta" in dashboard_data
                ), f"Upgrade CTA missing for scenario: {scenario['name']}"

                cta_data = dashboard_data["upgrade_cta"]
                assert (
                    cta_data["show"] is True
                ), f"Upgrade CTA should be shown for scenario: {scenario['name']}"

                if "cta_type" in scenario:
                    assert cta_data["type"] == scenario["cta_type"], (
                        f"Wrong CTA type for scenario {scenario['name']}: "
                        f"expected {scenario['cta_type']}, got {cta_data['type']}"
                    )

                # Verify CTA contains relevant information
                assert "message" in cta_data
                assert "recommended_tier" in cta_data
                assert "benefits" in cta_data

                # Check that message is appropriate for usage level
                message = cta_data["message"].lower()
                if scenario["cta_type"] == "blocked":
                    assert "limit" in message or "upgrade" in message
                elif scenario["cta_type"] == "urgent":
                    assert "almost" in message or "critical" in message
                elif scenario["cta_type"] == "warning":
                    assert "approaching" in message or "consider" in message

            else:
                # Should not show upgrade CTA for low usage
                if "upgrade_cta" in dashboard_data:
                    assert (
                        dashboard_data["upgrade_cta"]["show"] is False
                    ), f"Upgrade CTA should not be shown for scenario: {scenario['name']}"


class TestROICalculator:
    """Test ROI calculator accuracy and edge cases."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_roi_calculator_accuracy(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test ROI calculator with edge cases and various scenarios.

        Validates accurate ROI calculations for different usage patterns.
        """
        user = test_users_db["user"]

        # Test scenarios with different ROI calculations
        roi_scenarios = [
            {
                "name": "High ROI Scenario",
                "input": {
                    "current_tier": "free",
                    "target_tier": "reader_pro",
                    "monthly_usage": {"parses": 1500, "plans": 50, "executions": 25},
                    "time_saved_hours_per_month": 40,
                    "hourly_rate": 75,
                },
                "expected_roi": {
                    "monthly_savings": 3000,  # 40 hours * $75
                    "monthly_cost": 129,  # Reader Pro cost
                    "roi_percentage": 2225,  # ((3000 - 129) / 129) * 100
                },
            },
            {
                "name": "Break-even Scenario",
                "input": {
                    "current_tier": "free",
                    "target_tier": "planner_pro",
                    "monthly_usage": {"parses": 500, "plans": 75, "executions": 35},
                    "time_saved_hours_per_month": 3,
                    "hourly_rate": 75,
                },
                "expected_roi": {
                    "monthly_savings": 225,  # 3 hours * $75
                    "monthly_cost": 229,  # Planner Pro cost
                    "roi_percentage": -2,  # ((225 - 229) / 229) * 100
                },
            },
            {
                "name": "Enterprise Scenario",
                "input": {
                    "current_tier": "complete_platform",
                    "target_tier": "enterprise",
                    "monthly_usage": {
                        "parses": 10000,
                        "plans": 2000,
                        "executions": 1000,
                    },
                    "time_saved_hours_per_month": 200,
                    "hourly_rate": 150,
                    "team_size": 10,
                },
                "expected_roi": {
                    "monthly_savings": 30000,  # 200 hours * $150 * 10 people
                    "monthly_cost": 1499,  # Enterprise cost
                    "roi_percentage": 1901,  # ((30000 - 1499) / 1499) * 100
                },
            },
        ]

        for scenario in roi_scenarios:
            # Call ROI calculator endpoint
            response = test_client.post(
                "/api/v1/analytics/roi-calculator",
                json=scenario["input"],
                headers=auth_headers["user"],
            )

            assert (
                response.status_code == 200
            ), f"ROI calculator failed for scenario: {scenario['name']}"

            roi_data = response.json()

            # Verify ROI calculation accuracy
            expected = scenario["expected_roi"]

            # Check monthly savings calculation
            assert "monthly_savings" in roi_data
            savings_diff = abs(
                roi_data["monthly_savings"] - expected["monthly_savings"]
            )
            assert savings_diff <= expected["monthly_savings"] * 0.05, (
                f"Monthly savings calculation off for {scenario['name']}: "
                f"expected {expected['monthly_savings']}, got {roi_data['monthly_savings']}"
            )

            # Check monthly cost
            assert "monthly_cost" in roi_data
            cost_diff = abs(roi_data["monthly_cost"] - expected["monthly_cost"])
            assert cost_diff <= 1, (
                f"Monthly cost incorrect for {scenario['name']}: "
                f"expected {expected['monthly_cost']}, got {roi_data['monthly_cost']}"
            )

            # Check ROI percentage
            assert "roi_percentage" in roi_data
            roi_diff = abs(roi_data["roi_percentage"] - expected["roi_percentage"])
            assert roi_diff <= 10, (
                f"ROI percentage calculation off for {scenario['name']}: "
                f"expected {expected['roi_percentage']}%, got {roi_data['roi_percentage']}%"
            )

            # Verify additional metrics
            assert "payback_period_months" in roi_data
            assert "annual_savings" in roi_data
            assert "cost_per_hour_saved" in roi_data

            # Payback period should be reasonable
            if roi_data["roi_percentage"] > 0:
                assert roi_data["payback_period_months"] > 0
                assert (
                    roi_data["payback_period_months"] <= 12
                )  # Should pay back within a year for positive ROI

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_roi_edge_cases(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test ROI calculator edge cases and error handling.

        Validates proper handling of invalid inputs and edge cases.
        """
        edge_cases = [
            {
                "name": "Zero time savings",
                "input": {
                    "current_tier": "free",
                    "target_tier": "reader_pro",
                    "monthly_usage": {"parses": 1000, "plans": 50, "executions": 25},
                    "time_saved_hours_per_month": 0,
                    "hourly_rate": 75,
                },
                "expected_result": "negative_roi",
            },
            {
                "name": "Very high hourly rate",
                "input": {
                    "current_tier": "free",
                    "target_tier": "reader_pro",
                    "monthly_usage": {"parses": 100, "plans": 5, "executions": 2},
                    "time_saved_hours_per_month": 1,
                    "hourly_rate": 10000,
                },
                "expected_result": "high_roi",
            },
            {
                "name": "Invalid tier combination",
                "input": {
                    "current_tier": "enterprise",
                    "target_tier": "free",  # Downgrade
                    "monthly_usage": {"parses": 1000, "plans": 100, "executions": 50},
                    "time_saved_hours_per_month": 10,
                    "hourly_rate": 75,
                },
                "expected_result": "error",
            },
            {
                "name": "Negative hourly rate",
                "input": {
                    "current_tier": "free",
                    "target_tier": "reader_pro",
                    "monthly_usage": {"parses": 1000, "plans": 50, "executions": 25},
                    "time_saved_hours_per_month": 10,
                    "hourly_rate": -50,
                },
                "expected_result": "error",
            },
        ]

        for case in edge_cases:
            response = test_client.post(
                "/api/v1/analytics/roi-calculator",
                json=case["input"],
                headers=auth_headers["user"],
            )

            if case["expected_result"] == "error":
                assert response.status_code in [
                    400,
                    422,
                ], f"Should return error for case: {case['name']}"

                if response.status_code in [400, 422]:
                    error_data = response.json()
                    assert "error" in error_data or "detail" in error_data

            elif case["expected_result"] == "negative_roi":
                assert response.status_code == 200
                roi_data = response.json()
                assert (
                    roi_data["roi_percentage"] < 0
                ), f"Should have negative ROI for case: {case['name']}"

            elif case["expected_result"] == "high_roi":
                assert response.status_code == 200
                roi_data = response.json()
                assert (
                    roi_data["roi_percentage"] > 1000
                ), f"Should have very high ROI for case: {case['name']}"


class TestBillingIntegration:
    """Test billing integration accuracy and data consistency."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_stripe_billing_events_accuracy(self, test_db, test_users_db):
        """
        Cross-check Stripe billing events with usage logs.

        Validates that billing events match actual usage data.
        """
        user = test_users_db["user"]

        # Set up user with metered billing
        await subscription_service.update_user_subscription(
            test_db,
            user.id,
            {
                "tier": "planner_pro",
                "billing_type": "metered",
                "base_price": 229.00,
                "overage_rates": {"plans": 5.00, "executions": 2.00},
            },
        )

        # Simulate usage events over a billing period
        usage_events = [
            {
                "type": "plans_used",
                "amount": 15,
                "timestamp": datetime.utcnow() - timedelta(days=25),
            },
            {
                "type": "plans_used",
                "amount": 20,
                "timestamp": datetime.utcnow() - timedelta(days=20),
            },
            {
                "type": "plans_used",
                "amount": 25,
                "timestamp": datetime.utcnow() - timedelta(days=15),
            },
            {
                "type": "executions_used",
                "amount": 10,
                "timestamp": datetime.utcnow() - timedelta(days=10),
            },
            {
                "type": "executions_used",
                "amount": 15,
                "timestamp": datetime.utcnow() - timedelta(days=5),
            },
            {
                "type": "executions_used",
                "amount": 20,
                "timestamp": datetime.utcnow() - timedelta(days=2),
            },
        ]

        # Record usage events
        for event in usage_events:
            await analytics_service.track_usage_event(
                test_db, user.id, event["type"], event["amount"], event["timestamp"]
            )

        # Calculate expected billing
        total_plans = sum(
            e["amount"] for e in usage_events if e["type"] == "plans_used"
        )  # 60
        total_executions = sum(
            e["amount"] for e in usage_events if e["type"] == "executions_used"
        )  # 45

        plan_limit = 50  # Planner Pro limit
        execution_limit = 30  # Planner Pro limit

        plan_overage = max(0, total_plans - plan_limit)  # 10 plans over
        execution_overage = max(
            0, total_executions - execution_limit
        )  # 15 executions over

        expected_overage_cost = (plan_overage * 5.00) + (
            execution_overage * 2.00
        )  # $80
        expected_total = 229.00 + expected_overage_cost  # $309

        # Mock Stripe billing calculation
        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.InvoiceItem.create.return_value = MagicMock(id="ii_test123")
            mock_stripe.Invoice.create.return_value = MagicMock(
                id="in_test123",
                total=int(expected_total * 100),  # Stripe uses cents
                amount_due=int(expected_total * 100),
            )

            # Generate billing invoice
            billing_result = await billing_service.generate_monthly_invoice(
                test_db, user.id
            )

        # Verify billing accuracy
        assert billing_result["base_amount"] == 229.00
        assert billing_result["overage_amount"] == expected_overage_cost
        assert billing_result["total_amount"] == expected_total

        # Verify usage breakdown matches events
        assert billing_result["usage_summary"]["plans_used"] == total_plans
        assert billing_result["usage_summary"]["executions_used"] == total_executions

        # Verify Stripe integration calls
        mock_stripe.InvoiceItem.create.assert_called()
        mock_stripe.Invoice.create.assert_called()

        # Check that invoice items match usage
        stripe_calls = mock_stripe.InvoiceItem.create.call_args_list

        # Should have calls for base subscription and overages
        base_call = next(
            (call for call in stripe_calls if "Base subscription" in str(call)), None
        )
        assert base_call is not None, "Should have base subscription invoice item"

        if plan_overage > 0:
            plan_overage_call = next(
                (call for call in stripe_calls if "plan" in str(call).lower()), None
            )
            assert (
                plan_overage_call is not None
            ), "Should have plan overage invoice item"

        if execution_overage > 0:
            exec_overage_call = next(
                (call for call in stripe_calls if "execution" in str(call).lower()),
                None,
            )
            assert (
                exec_overage_call is not None
            ), "Should have execution overage invoice item"


class TestAuditLogExports:
    """Test audit log export functionality and data integrity."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_audit_log_export_formats(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test audit log export in CSV/JSON formats.

        Validates that audit logs can be exported in multiple formats with data integrity.
        """
        user = test_users_db["admin"]  # Admin user for audit log access

        # Generate audit log entries by performing various actions
        test_actions = [
            (
                "POST",
                "/api/v1/tasks/",
                {"title": "Audit Test Task 1", "description": "Test", "goal": "Test"},
            ),
            ("GET", "/api/v1/tasks/", None),
            ("PUT", "/api/v1/users/me", {"full_name": "Updated Admin Name"}),
            ("POST", "/api/v1/auth/logout", None),
            (
                "POST",
                "/api/v1/auth/login",
                {"email": user.email, "password": "TestAdmin123!"},
            ),
        ]

        # Perform actions to generate audit logs
        for method, endpoint, payload in test_actions:
            if method == "POST":
                if payload:
                    response = test_client.post(
                        endpoint, json=payload, headers=auth_headers["admin"]
                    )
                else:
                    response = test_client.post(endpoint, headers=auth_headers["admin"])
            elif method == "GET":
                response = test_client.get(endpoint, headers=auth_headers["admin"])
            elif method == "PUT":
                response = test_client.put(
                    endpoint, json=payload, headers=auth_headers["admin"]
                )

            # Allow time for audit log creation
            await asyncio.sleep(0.5)

        # Test CSV export
        csv_response = test_client.get(
            "/api/v1/security/audit-logs/export?format=csv&start_date=2024-01-01&end_date=2025-12-31",
            headers=auth_headers["admin"],
        )

        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"] == "text/csv"

        # Parse CSV content
        csv_content = csv_response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        csv_rows = list(csv_reader)

        # Verify CSV structure and content
        assert len(csv_rows) >= len(
            test_actions
        ), "Should have audit logs for all actions"

        required_csv_columns = [
            "timestamp",
            "user_id",
            "user_email",
            "action",
            "resource",
            "ip_address",
            "user_agent",
            "status",
            "details",
        ]

        for column in required_csv_columns:
            assert (
                column in csv_reader.fieldnames
            ), f"CSV missing required column: {column}"

        # Verify data integrity in CSV
        for row in csv_rows[-len(test_actions) :]:  # Check recent entries
            assert row["user_id"] == str(user.id)
            assert row["user_email"] == user.email
            assert row["action"] in [
                f"{method} {endpoint}" for method, endpoint, _ in test_actions
            ]
            assert row["timestamp"]  # Should have timestamp
            assert row["ip_address"]  # Should have IP

        # Test JSON export
        json_response = test_client.get(
            "/api/v1/security/audit-logs/export?format=json&start_date=2024-01-01&end_date=2025-12-31",
            headers=auth_headers["admin"],
        )

        assert json_response.status_code == 200
        assert json_response.headers["content-type"] == "application/json"

        # Parse JSON content
        json_data = json_response.json()

        assert "audit_logs" in json_data
        assert "metadata" in json_data

        audit_logs = json_data["audit_logs"]
        assert len(audit_logs) >= len(test_actions)

        # Verify JSON structure and content
        for log_entry in audit_logs[-len(test_actions) :]:  # Check recent entries
            required_json_fields = [
                "id",
                "timestamp",
                "user_id",
                "user_email",
                "action",
                "resource",
                "ip_address",
                "user_agent",
                "status",
                "details",
            ]

            for field in required_json_fields:
                assert field in log_entry, f"JSON missing required field: {field}"

            assert log_entry["user_id"] == user.id
            assert log_entry["user_email"] == user.email

        # Verify metadata
        metadata = json_data["metadata"]
        assert "export_timestamp" in metadata
        assert "total_records" in metadata
        assert "date_range" in metadata
        assert metadata["total_records"] == len(audit_logs)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_audit_log_data_retention(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test data retention policies (GDPR deletion requests).

        Validates that audit logs respect data retention and deletion policies.
        """
        user = test_users_db["user"]
        admin = test_users_db["admin"]

        # Create audit logs for the user
        test_actions = [
            "login",
            "create_task",
            "view_dashboard",
            "update_profile",
            "logout",
        ]

        # Simulate audit log creation (in real scenario, these would be created by actual actions)

        audit_logs = []
        for i, action in enumerate(test_actions):
            audit_log = AuditLog(
                user_id=user.id,
                action=action,
                resource="test_resource",
                ip_address="192.168.1.100",
                user_agent="Test User Agent",
                status="success",
                details={"test": f"action_{i}"},
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            test_db.add(audit_log)
            audit_logs.append(audit_log)

        await test_db.commit()

        # Verify audit logs exist
        initial_response = test_client.get(
            f"/api/v1/security/audit-logs?user_id={user.id}",
            headers=auth_headers["admin"],
        )
        assert initial_response.status_code == 200
        initial_logs = initial_response.json()
        assert len(initial_logs) >= len(test_actions)

        # Test GDPR deletion request
        gdpr_response = test_client.post(
            "/api/v1/users/gdpr/delete-data",
            json={
                "user_id": user.id,
                "data_types": ["audit_logs"],
                "reason": "User requested data deletion",
                "retain_anonymous": True,  # Keep anonymized logs for compliance
            },
            headers=auth_headers["admin"],
        )

        assert gdpr_response.status_code == 200
        deletion_result = gdpr_response.json()

        assert "deletion_id" in deletion_result
        assert "status" in deletion_result
        assert deletion_result["status"] in ["completed", "processing"]

        # Wait for deletion processing
        await asyncio.sleep(2)

        # Verify audit logs are anonymized/deleted
        post_deletion_response = test_client.get(
            f"/api/v1/security/audit-logs?user_id={user.id}",
            headers=auth_headers["admin"],
        )

        if post_deletion_response.status_code == 200:
            post_deletion_logs = post_deletion_response.json()

            # If logs still exist, they should be anonymized
            for log in post_deletion_logs:
                if log["user_id"] == user.id:
                    # Should be anonymized
                    assert (
                        log["user_email"] == "anonymized@deleted.user"
                        or log["user_email"] is None
                    )
                    assert (
                        "anonymized" in log.get("details", {}).get("status", "").lower()
                    )
        else:
            # Logs completely removed
            assert post_deletion_response.status_code == 404

        # Test retention policy enforcement
        retention_response = test_client.post(
            "/api/v1/security/audit-logs/apply-retention",
            json={"retention_days": 30, "dry_run": False},
            headers=auth_headers["admin"],
        )

        assert retention_response.status_code == 200
        retention_result = retention_response.json()

        assert "deleted_count" in retention_result
        assert "retained_count" in retention_result

        # Verify old logs are removed
        final_response = test_client.get(
            "/api/v1/security/audit-logs?start_date=2024-01-01",
            headers=auth_headers["admin"],
        )

        if final_response.status_code == 200:
            final_logs = final_response.json()

            # All remaining logs should be within retention period
            cutoff_date = datetime.utcnow() - timedelta(days=30)

            for log in final_logs:
                log_date = datetime.fromisoformat(
                    log["timestamp"].replace("Z", "+00:00")
                )
                assert (
                    log_date >= cutoff_date
                ), f"Log older than retention period found: {log['timestamp']}"


class TestDataIntegrityValidation:
    """Test data integrity across analytics and reporting systems."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_system_data_consistency(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test data consistency across analytics, billing, and audit systems.

        Validates that the same events are recorded consistently across all systems.
        """
        user = test_users_db["user"]

        # Perform a series of actions that should be recorded in multiple systems
        test_sequence = [
            {
                "action": "create_task",
                "endpoint": "/api/v1/tasks/",
                "payload": {
                    "title": "Consistency Test Task",
                    "description": "Test",
                    "goal": "Test consistency",
                },
                "expected_records": {
                    "analytics": {"event_type": "task_created"},
                    "audit": {"action": "POST /api/v1/tasks/"},
                    "billing": {"usage_type": "tasks_created"},
                },
            },
            {
                "action": "parse_webpage",
                "endpoint": "/api/v1/web-pages/parse",
                "payload": {
                    "url": "https://httpbin.org/forms/post",
                    "force_refresh": False,
                },
                "expected_records": {
                    "analytics": {"event_type": "webpage_parsed"},
                    "audit": {"action": "POST /api/v1/web-pages/parse"},
                    "billing": {"usage_type": "parses_used"},
                },
            },
        ]

        for sequence_item in test_sequence:
            # Record timestamp before action
            action_timestamp = datetime.utcnow()

            # Perform the action
            response = test_client.post(
                sequence_item["endpoint"],
                json=sequence_item["payload"],
                headers=auth_headers["user"],
            )

            assert response.status_code in [
                200,
                201,
                202,
            ], f"Action {sequence_item['action']} failed"

            # Wait for all systems to process
            await asyncio.sleep(3)

            # Check analytics system
            analytics_response = test_client.get(
                f"/api/v1/analytics/events?user_id={user.id}&start_time={action_timestamp.isoformat()}",
                headers=auth_headers["admin"],
            )

            if analytics_response.status_code == 200:
                analytics_events = analytics_response.json()
                expected_analytics = sequence_item["expected_records"]["analytics"]

                matching_events = [
                    event
                    for event in analytics_events
                    if event.get("event_type") == expected_analytics["event_type"]
                ]

                assert (
                    len(matching_events) > 0
                ), f"Analytics event not found for {sequence_item['action']}"

            # Check audit system
            audit_response = test_client.get(
                f"/api/v1/security/audit-logs?user_id={user.id}&start_time={action_timestamp.isoformat()}",
                headers=auth_headers["admin"],
            )

            if audit_response.status_code == 200:
                audit_logs = audit_response.json()
                expected_audit = sequence_item["expected_records"]["audit"]

                matching_audits = [
                    log
                    for log in audit_logs
                    if log.get("action") == expected_audit["action"]
                ]

                assert (
                    len(matching_audits) > 0
                ), f"Audit log not found for {sequence_item['action']}"

            # Check billing system
            billing_response = test_client.get(
                f"/api/v1/billing/usage?user_id={user.id}&start_time={action_timestamp.isoformat()}",
                headers=auth_headers["admin"],
            )

            if billing_response.status_code == 200:
                billing_usage = billing_response.json()
                expected_billing = sequence_item["expected_records"]["billing"]

                # Check if usage was incremented
                usage_type = expected_billing["usage_type"]
                if usage_type in billing_usage:
                    assert (
                        billing_usage[usage_type] > 0
                    ), f"Billing usage not incremented for {sequence_item['action']}"

        # Verify timestamp consistency across systems (should be within reasonable range)
        final_analytics = test_client.get(
            f"/api/v1/analytics/events?user_id={user.id}", headers=auth_headers["admin"]
        )

        final_audit = test_client.get(
            f"/api/v1/security/audit-logs?user_id={user.id}",
            headers=auth_headers["admin"],
        )

        if final_analytics.status_code == 200 and final_audit.status_code == 200:
            analytics_events = final_analytics.json()
            audit_logs = final_audit.json()

            # Find corresponding events and verify timestamps are close
            for analytics_event in analytics_events[-len(test_sequence) :]:
                analytics_time = datetime.fromisoformat(
                    analytics_event["timestamp"].replace("Z", "+00:00")
                )

                # Find corresponding audit log
                corresponding_audit = next(
                    (
                        log
                        for log in audit_logs
                        if abs(
                            (
                                datetime.fromisoformat(
                                    log["timestamp"].replace("Z", "+00:00")
                                )
                                - analytics_time
                            ).total_seconds()
                        )
                        < 10
                    ),
                    None,
                )

                if corresponding_audit:
                    audit_time = datetime.fromisoformat(
                        corresponding_audit["timestamp"].replace("Z", "+00:00")
                    )
                    time_diff = abs((analytics_time - audit_time).total_seconds())

                    assert (
                        time_diff < 5
                    ), f"Timestamp mismatch between analytics and audit: {time_diff}s difference"
