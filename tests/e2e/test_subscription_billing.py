"""
E2E Tests: Subscription & Billing
Tests for feature gating, usage limits, and billing integration
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.services.analytics_service import analytics_service
from app.services.billing_service import billing_service
from app.services.subscription_service import subscription_service


class TestSubscriptionBilling:
    """Test subscription tiers, feature gating, and billing integration."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_free_tier_usage_limits(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test feature gating at 80%/100% usage limits for Free tier.

        Validates that users are properly restricted when approaching limits.
        """
        user = test_users_db["user"]

        # Set user to free tier with specific limits
        await subscription_service.update_user_subscription(
            test_db,
            user.id,
            {
                "tier": "free",
                "limits": {"parses": 200, "plans": 20, "executions": 10},
                "usage": {"parses_used": 0, "plans_used": 0, "executions_used": 0},
            },
        )

        # Test parsing at 80% limit (160/200 parses)
        await subscription_service.update_usage(test_db, user.id, "parses_used", 160)

        # Should still allow parsing but show warning
        response = test_client.post(
            "/api/v1/web-pages/parse",
            json={"url": "https://httpbin.org/forms/post", "force_refresh": False},
            headers=auth_headers["user"],
        )

        assert response.status_code == 200
        data = response.json()

        # Should include usage warning in response
        assert "usage_warning" in data
        assert data["usage_warning"]["percentage"] >= 80

        # Test at 100% limit (200/200 parses)
        await subscription_service.update_usage(test_db, user.id, "parses_used", 200)

        # Should block further parsing
        response = test_client.post(
            "/api/v1/web-pages/parse",
            json={"url": "https://httpbin.org/forms/post", "force_refresh": False},
            headers=auth_headers["user"],
        )

        assert response.status_code == 429  # Too Many Requests
        data = response.json()
        assert "limit_exceeded" in data["error"]["message"].lower()
        assert "upgrade" in data["error"]["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_plan_upgrade_downgrade_flow(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test plan upgrade/downgrade with prorated billing.

        Validates billing calculations and feature access changes.
        """
        user = test_users_db["user"]

        # Start with free tier
        await subscription_service.update_user_subscription(
            test_db,
            user.id,
            {
                "tier": "free",
                "billing_cycle": "monthly",
                "next_billing_date": datetime.utcnow() + timedelta(days=30),
            },
        )

        # Mock Stripe integration for billing
        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
            mock_stripe.Subscription.create.return_value = MagicMock(
                id="sub_test123",
                current_period_end=int(
                    (datetime.utcnow() + timedelta(days=30)).timestamp()
                ),
            )

            # Upgrade to Individual Reader Pro
            response = test_client.post(
                "/api/v1/billing/upgrade",
                json={
                    "target_tier": "reader_pro",
                    "billing_cycle": "monthly",
                    "payment_method": "pm_test_card",
                },
                headers=auth_headers["user"],
            )

            assert response.status_code == 200
            data = response.json()

            # Verify upgrade response
            assert data["subscription"]["tier"] == "reader_pro"
            assert data["subscription"]["status"] == "active"
            assert "proration_amount" in data

            # Verify Stripe calls
            mock_stripe.Customer.create.assert_called_once()
            mock_stripe.Subscription.create.assert_called_once()

        # Verify user now has access to Reader Pro features
        subscription = await subscription_service.get_user_subscription(
            test_db, user.id
        )
        assert subscription["tier"] == "reader_pro"
        assert subscription["limits"]["parses"] == 2000  # Reader Pro limit

        # Test feature access
        response = test_client.get(
            "/api/v1/analytics/reader", headers=auth_headers["user"]
        )
        assert response.status_code == 200  # Should have access to Reader analytics

        # Test downgrade scenario
        with patch("app.services.billing_service.stripe") as mock_stripe:
            mock_stripe.Subscription.modify.return_value = MagicMock(
                id="sub_test123", cancel_at_period_end=True
            )

            # Downgrade to free at end of billing period
            response = test_client.post(
                "/api/v1/billing/downgrade",
                json={"target_tier": "free", "effective_date": "end_of_period"},
                headers=auth_headers["user"],
            )

            assert response.status_code == 200
            data = response.json()

            # Should schedule downgrade, not immediate
            assert data["scheduled_change"]["target_tier"] == "free"
            assert data["scheduled_change"]["effective_date"] is not None

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_automatic_downgrade_after_cancellation(self, test_db, test_users_db):
        """
        Test automatic downgrades after subscription cancellation.

        Validates that users lose access to premium features appropriately.
        """
        user = test_users_db["manager"]

        # Set user to Complete Platform tier
        await subscription_service.update_user_subscription(
            test_db,
            user.id,
            {
                "tier": "complete_platform",
                "status": "active",
                "billing_cycle": "monthly",
                "next_billing_date": datetime.utcnow() + timedelta(days=5),
            },
        )

        # Simulate subscription cancellation
        await subscription_service.cancel_subscription(
            test_db,
            user.id,
            {
                "reason": "user_requested",
                "effective_date": datetime.utcnow() + timedelta(days=5),
            },
        )

        # Verify subscription is marked for cancellation
        subscription = await subscription_service.get_user_subscription(
            test_db, user.id
        )
        assert subscription["status"] == "cancel_at_period_end"

        # Simulate time passing to cancellation date
        with patch("app.services.subscription_service.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(days=6)

            # Run subscription cleanup job
            await subscription_service.process_expired_subscriptions(test_db)

        # Verify user is downgraded to free tier
        updated_subscription = await subscription_service.get_user_subscription(
            test_db, user.id
        )
        assert updated_subscription["tier"] == "free"
        assert updated_subscription["status"] == "inactive"

        # Verify limits are reduced
        assert updated_subscription["limits"]["parses"] == 200  # Free tier limit
        assert updated_subscription["limits"]["plans"] == 20
        assert updated_subscription["limits"]["executions"] == 10

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_enterprise_tier_features(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test Enterprise tier exclusive features and unlimited usage.

        Validates enterprise-only functionality and billing.
        """
        admin_user = test_users_db["admin"]

        # Set admin to Enterprise tier
        await subscription_service.update_user_subscription(
            test_db,
            admin_user.id,
            {
                "tier": "enterprise",
                "status": "active",
                "billing_cycle": "annual",
                "limits": {
                    "parses": -1,  # Unlimited
                    "plans": -1,  # Unlimited
                    "executions": -1,  # Unlimited
                    "api_calls": -1,  # Unlimited
                    "storage_gb": 1000,  # 1TB
                },
                "features": [
                    "unlimited_usage",
                    "priority_support",
                    "custom_integrations",
                    "advanced_analytics",
                    "white_label",
                    "sla_guarantee",
                ],
            },
        )

        # Test unlimited usage - should never hit limits
        for i in range(300):  # Exceed free tier limits
            response = test_client.post(
                "/api/v1/web-pages/parse",
                json={
                    "url": f"https://httpbin.org/forms/post?test={i}",
                    "force_refresh": True,
                },
                headers=auth_headers["admin"],
            )

            if i % 50 == 0:  # Check every 50 requests
                assert response.status_code == 200
                # Should never show usage warnings for enterprise
                data = response.json()
                assert "usage_warning" not in data

        # Test enterprise-only analytics endpoint
        response = test_client.get(
            "/api/v1/analytics/enterprise/advanced", headers=auth_headers["admin"]
        )
        assert response.status_code == 200

        data = response.json()
        assert "advanced_metrics" in data
        assert "cost_analysis" in data
        assert "roi_projections" in data

        # Test white-label customization
        response = test_client.post(
            "/api/v1/enterprise/branding",
            json={
                "logo_url": "https://example.com/logo.png",
                "primary_color": "#1a365d",
                "company_name": "Test Enterprise Corp",
            },
            headers=auth_headers["admin"],
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_billing_integration_accuracy(self, test_db, test_users_db):
        """
        Test billing integration accuracy with usage tracking.

        Validates that usage is correctly tracked and billed.
        """
        user = test_users_db["user"]

        # Set user to Individual Planner Pro (metered billing)
        await subscription_service.update_user_subscription(
            test_db,
            user.id,
            {
                "tier": "planner_pro",
                "billing_type": "metered",
                "base_price": 229.00,
                "overage_rates": {
                    "plans": 5.00,  # $5 per plan over limit
                    "executions": 2.00,  # $2 per execution over limit
                },
            },
        )

        # Simulate usage over the billing period
        usage_events = [
            {
                "type": "plans_used",
                "amount": 25,
                "timestamp": datetime.utcnow() - timedelta(days=20),
            },
            {
                "type": "plans_used",
                "amount": 30,
                "timestamp": datetime.utcnow() - timedelta(days=15),
            },
            {
                "type": "executions_used",
                "amount": 15,
                "timestamp": datetime.utcnow() - timedelta(days=10),
            },
            {
                "type": "executions_used",
                "amount": 20,
                "timestamp": datetime.utcnow() - timedelta(days=5),
            },
        ]

        for event in usage_events:
            await analytics_service.track_usage_event(
                test_db, user.id, event["type"], event["amount"], event["timestamp"]
            )

        # Calculate expected billing
        total_plans = 55  # 25 + 30
        total_executions = 35  # 15 + 20

        plan_limit = 50  # Planner Pro limit
        execution_limit = 30  # Planner Pro limit

        plan_overage = max(0, total_plans - plan_limit)  # 5 plans over
        execution_overage = max(
            0, total_executions - execution_limit
        )  # 5 executions over

        expected_overage_cost = (plan_overage * 5.00) + (
            execution_overage * 2.00
        )  # $35
        expected_total = 229.00 + expected_overage_cost  # $264

        # Generate billing calculation
        billing_data = await billing_service.calculate_monthly_bill(test_db, user.id)

        assert billing_data["base_amount"] == 229.00
        assert billing_data["overage_amount"] == expected_overage_cost
        assert billing_data["total_amount"] == expected_total

        # Verify usage breakdown
        assert billing_data["usage_summary"]["plans_used"] == total_plans
        assert billing_data["usage_summary"]["executions_used"] == total_executions
        assert billing_data["overage_details"]["plans_over"] == plan_overage
        assert billing_data["overage_details"]["executions_over"] == execution_overage

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_subscription_analytics_accuracy(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test subscription analytics and revenue optimization features.

        Validates analytics accuracy and upgrade prompts.
        """
        user = test_users_db["user"]

        # Set user to free tier with high usage
        await subscription_service.update_user_subscription(
            test_db,
            user.id,
            {
                "tier": "free",
                "usage": {
                    "parses_used": 180,  # 90% of limit
                    "plans_used": 18,  # 90% of limit
                    "executions_used": 8,  # 80% of limit
                },
            },
        )

        # Get dashboard analytics
        response = test_client.get(
            "/api/v1/analytics/dashboard", headers=auth_headers["user"]
        )

        assert response.status_code == 200
        data = response.json()

        # Verify usage percentages are calculated correctly
        assert data["subscription"]["usage_percentages"]["parses"] == 90
        assert data["subscription"]["usage_percentages"]["plans"] == 90
        assert data["subscription"]["usage_percentages"]["executions"] == 80

        # Should show upgrade recommendations
        assert "upgrade_recommendations" in data
        recommendations = data["upgrade_recommendations"]

        # Should recommend Reader Pro due to high parsing usage
        reader_rec = next(
            (r for r in recommendations if r["target_tier"] == "reader_pro"), None
        )
        assert reader_rec is not None
        assert reader_rec["confidence_score"] > 0.8
        assert "parsing" in reader_rec["reason"].lower()

        # Should calculate potential savings
        assert "potential_savings" in reader_rec
        assert reader_rec["potential_savings"]["monthly"] > 0

        # Test conversion tracking
        response = test_client.post(
            "/api/v1/analytics/track-event",
            json={
                "event_type": "upgrade_cta_clicked",
                "event_data": {
                    "target_tier": "reader_pro",
                    "source": "dashboard_usage_warning",
                    "usage_percentage": 90,
                },
            },
            headers=auth_headers["user"],
        )

        assert response.status_code == 200

        # Verify event was tracked
        events = await analytics_service.get_user_events(
            test_db, user.id, "upgrade_cta_clicked"
        )
        assert len(events) > 0
        assert events[0]["event_data"]["target_tier"] == "reader_pro"
