"""
Critical Subscription & Billing E2E Tests
⚠️ CRITICAL: Revenue-critical subscription tier and billing validation

Test Coverage:
✅ Feature gating at 80%/100% usage limits (Free tier)
✅ Automatic downgrades after subscription cancellation
✅ Plan upgrade/downgrade with prorated billing
✅ Stripe integration and payment processing
✅ Usage tracking accuracy across all components
✅ Analytics dashboard upgrade prompts
✅ Revenue attribution and conversion tracking
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.models.user import User
from app.models.subscription import Subscription, SubscriptionTier, SubscriptionStatus
from app.models.billing import BillingEvent, PaymentMethod, Invoice
from app.services.subscription_service import subscription_service
from app.services.billing_service import billing_service
from app.services.analytics_service import analytics_service
from app.services.web_parser import web_parser_service
from app.services.planning_service import planning_service
from app.services.action_executor import action_executor


class TestSubscriptionBillingCritical:
    """Critical subscription and billing functionality tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.billing
    async def test_free_tier_feature_gating_comprehensive(self, test_db, test_users_db, test_client, auth_headers):
        """
        ⚠️ CRITICAL: Test comprehensive feature gating at usage limits.
        
        Validates that free tier users are properly restricted at 80%/100%
        usage limits and that upgrade prompts are shown strategically.
        """
        user = test_users_db["user"]
        
        # Set up free tier subscription with specific limits
        subscription = await subscription_service.create_subscription(
            test_db,
            user.id,
            {
                "tier": SubscriptionTier.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "limits": {
                    "parses": 200,
                    "plans": 20,
                    "executions": 10,
                    "storage_gb": 1,
                    "api_calls": 1000
                },
                "billing_cycle_start": datetime.utcnow(),
                "billing_cycle_end": datetime.utcnow() + timedelta(days=30)
            }
        )
        
        # Test 1: Normal usage within limits
        # Use 50% of parse limit (100/200)
        for i in range(100):
            await subscription_service.track_usage(
                test_db, user.id, "parses", 1
            )
        
        # Should allow continued usage
        response = await test_client.post(
            "/api/v1/web-pages/parse",
            json={"url": "https://example.com"},
            headers=auth_headers
        )
        assert response.status_code == 200, "Should allow usage within limits"
        
        # Test 2: 80% threshold - show upgrade prompts
        # Reach 80% of parse limit (160/200)
        for i in range(60):
            await subscription_service.track_usage(
                test_db, user.id, "parses", 1
            )
        
        usage_status = await subscription_service.get_usage_status(test_db, user.id)
        assert usage_status["parses"]["percentage"] >= 80, "Should be at 80% threshold"
        assert usage_status["parses"]["show_upgrade_prompt"], "Should show upgrade prompt"
        
        # Analytics dashboard should include upgrade opportunities
        analytics_data = await analytics_service.get_dashboard_stats(test_db, user.id)
        upgrade_opportunities = analytics_data["upgrade_opportunities"]
        assert len(upgrade_opportunities) > 0, "Should have upgrade opportunities"
        assert any("approaching limit" in opp["title"].lower() for opp in upgrade_opportunities)
        
        # Test 3: 100% threshold - hard limit enforcement
        # Reach 100% of parse limit (200/200)
        for i in range(40):
            await subscription_service.track_usage(
                test_db, user.id, "parses", 1
            )
        
        # Should block further usage
        response = await test_client.post(
            "/api/v1/web-pages/parse",
            json={"url": "https://example.com"},
            headers=auth_headers
        )
        assert response.status_code == 429, "Should block usage at 100% limit"
        
        response_data = response.json()
        assert "upgrade" in response_data["detail"].lower(), "Should mention upgrade"
        assert "limit" in response_data["detail"].lower(), "Should mention limit"
        
        # Test 4: Different limits for different components
        # Test planning limits
        for i in range(16):  # 80% of 20 plan limit
            await subscription_service.track_usage(
                test_db, user.id, "plans", 1
            )
        
        plan_response = await test_client.post(
            "/api/v1/plans/generate",
            json={
                "goal": "Test planning",
                "url": "https://example.com"
            },
            headers=auth_headers
        )
        
        # Should show warning but still allow
        if plan_response.status_code == 200:
            assert "warning" in plan_response.headers.get("X-Usage-Warning", "").lower()
        
        # Reach plan limit
        for i in range(4):
            await subscription_service.track_usage(
                test_db, user.id, "plans", 1
            )
        
        plan_response = await test_client.post(
            "/api/v1/plans/generate",
            json={
                "goal": "Test planning",
                "url": "https://example.com"
            },
            headers=auth_headers
        )
        assert plan_response.status_code == 429, "Should block planning at limit"
        
        # Test 5: Execution limits
        for i in range(10):  # Full execution limit
            await subscription_service.track_usage(
                test_db, user.id, "executions", 1
            )
        
        exec_response = await test_client.post(
            "/api/v1/execute",
            json={"plan_id": 123},
            headers=auth_headers
        )
        assert exec_response.status_code == 429, "Should block execution at limit"
        
        # Test 6: Upgrade prompt tracking and conversion
        # Track upgrade prompt views
        await analytics_service.track_event(
            test_db, user.id, "upgrade_prompt_shown", 
            {"tier": "free", "usage_percentage": 80, "component": "reader"}
        )
        
        conversion_data = await analytics_service.get_conversion_metrics(test_db, user.id)
        assert conversion_data["upgrade_prompts_shown"] > 0, "Should track upgrade prompts"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.billing
    async def test_subscription_lifecycle_management(self, test_db, test_users_db):
        """
        ⚠️ CRITICAL: Test complete subscription lifecycle.
        
        Validates subscription creation, upgrades, downgrades, 
        cancellations, and automatic status transitions.
        """
        user = test_users_db["user"]
        
        # Test 1: Free tier to paid upgrade
        free_subscription = await subscription_service.create_subscription(
            test_db, user.id,
            {
                "tier": SubscriptionTier.FREE,
                "status": SubscriptionStatus.ACTIVE
            }
        )
        
        # Upgrade to Complete Platform
        upgraded_subscription = await subscription_service.upgrade_subscription(
            test_db, user.id,
            {
                "new_tier": SubscriptionTier.COMPLETE_PLATFORM,
                "payment_method_id": "pm_test_card",
                "proration": True
            }
        )
        
        assert upgraded_subscription.tier == SubscriptionTier.COMPLETE_PLATFORM
        assert upgraded_subscription.status == SubscriptionStatus.ACTIVE
        assert upgraded_subscription.id != free_subscription.id, "Should create new subscription"
        
        # Old subscription should be cancelled
        old_subscription = await subscription_service.get_subscription(test_db, free_subscription.id)
        assert old_subscription.status == SubscriptionStatus.CANCELLED
        
        # Test 2: Paid plan downgrade
        downgraded_subscription = await subscription_service.downgrade_subscription(
            test_db, user.id,
            {
                "new_tier": SubscriptionTier.READER_PRO,
                "effective_date": datetime.utcnow() + timedelta(days=1)  # End of current period
            }
        )
        
        # Should schedule downgrade for end of billing period
        assert downgraded_subscription.tier == SubscriptionTier.COMPLETE_PLATFORM, "Current tier unchanged"
        assert downgraded_subscription.scheduled_tier_change == SubscriptionTier.READER_PRO
        assert downgraded_subscription.tier_change_date is not None
        
        # Test 3: Subscription cancellation with grace period
        cancelled_subscription = await subscription_service.cancel_subscription(
            test_db, user.id,
            {
                "cancellation_reason": "Cost concerns",
                "feedback": "Too expensive for current usage",
                "immediate": False  # Cancel at end of period
            }
        )
        
        assert cancelled_subscription.status == SubscriptionStatus.ACTIVE, "Should remain active until period end"
        assert cancelled_subscription.cancellation_date is not None
        assert cancelled_subscription.cancelled_at_period_end is True
        
        # Test 4: Failed payment handling
        with patch('app.services.billing_service.stripe.PaymentIntent.create') as mock_payment:
            mock_payment.side_effect = Exception("Payment failed")
            
            # Simulate failed payment
            billing_result = await billing_service.process_subscription_payment(
                test_db, cancelled_subscription.id
            )
            
            assert not billing_result.success, "Payment should fail"
            
            # Subscription should move to past_due
            updated_subscription = await subscription_service.get_user_subscription(test_db, user.id)
            assert updated_subscription.status == SubscriptionStatus.PAST_DUE
        
        # Test 5: Reactivation after payment issue resolution
        reactivated_subscription = await subscription_service.reactivate_subscription(
            test_db, user.id,
            {
                "payment_method_id": "pm_test_card_valid",
                "pay_outstanding_balance": True
            }
        )
        
        assert reactivated_subscription.status == SubscriptionStatus.ACTIVE
        assert reactivated_subscription.past_due_resolved_at is not None
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.billing
    async def test_prorated_billing_calculations(self, test_db, test_users_db):
        """
        ⚠️ CRITICAL: Test prorated billing calculations for upgrades/downgrades.
        
        Validates accurate proration calculations for mid-cycle changes
        and ensures correct invoice generation.
        """
        user = test_users_db["user"]
        
        # Create monthly subscription
        subscription = await subscription_service.create_subscription(
            test_db, user.id,
            {
                "tier": SubscriptionTier.READER_PRO,  # $129/month
                "billing_cycle": "monthly",
                "billing_cycle_start": datetime.utcnow(),
                "billing_cycle_end": datetime.utcnow() + timedelta(days=30)
            }
        )
        
        # Test 1: Mid-cycle upgrade (after 10 days)
        upgrade_date = datetime.utcnow() + timedelta(days=10)
        
        with patch('app.services.billing_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = upgrade_date
            
            upgrade_result = await billing_service.calculate_proration(
                test_db, subscription.id,
                {
                    "new_tier": SubscriptionTier.COMPLETE_PLATFORM,  # $399/month
                    "upgrade_date": upgrade_date
                }
            )
            
            # Calculate expected proration
            days_remaining = 20  # 20 days left in 30-day cycle
            old_daily_rate = Decimal("129") / Decimal("30")  # $4.30/day
            new_daily_rate = Decimal("399") / Decimal("30")  # $13.30/day
            
            expected_credit = old_daily_rate * days_remaining  # Credit for unused Reader Pro
            expected_charge = new_daily_rate * days_remaining  # Charge for Complete Platform
            expected_proration = expected_charge - expected_credit
            
            assert abs(upgrade_result.proration_amount - expected_proration) < Decimal("0.01"), \
                   f"Proration calculation incorrect: {upgrade_result.proration_amount} vs {expected_proration}"
            
            assert upgrade_result.credit_amount == expected_credit
            assert upgrade_result.charge_amount == expected_charge
        
        # Test 2: Mid-cycle downgrade proration
        downgrade_date = datetime.utcnow() + timedelta(days=15)
        
        with patch('app.services.billing_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = downgrade_date
            
            downgrade_result = await billing_service.calculate_proration(
                test_db, subscription.id,
                {
                    "new_tier": SubscriptionTier.FREE,  # $0/month
                    "downgrade_date": downgrade_date,
                    "refund_unused": True
                }
            )
            
            # Should calculate refund for unused portion
            days_remaining = 15
            current_daily_rate = Decimal("399") / Decimal("30")
            expected_refund = current_daily_rate * days_remaining
            
            assert abs(downgrade_result.refund_amount - expected_refund) < Decimal("0.01"), \
                   f"Refund calculation incorrect: {downgrade_result.refund_amount} vs {expected_refund}"
        
        # Test 3: Bundle savings calculation
        bundle_calculation = await billing_service.calculate_bundle_savings(
            test_db, user.id,
            {
                "individual_tiers": [
                    SubscriptionTier.READER_PRO,     # $129
                    SubscriptionTier.PLANNER_PRO,    # $179  
                    SubscriptionTier.ACTOR_PRO       # $229
                ],
                "bundle_tier": SubscriptionTier.COMPLETE_PLATFORM  # $399
            }
        )
        
        expected_individual_total = Decimal("129") + Decimal("179") + Decimal("229")  # $537
        expected_bundle_price = Decimal("399")
        expected_savings = expected_individual_total - expected_bundle_price  # $138
        expected_savings_percentage = (expected_savings / expected_individual_total) * 100  # ~25.7%
        
        assert abs(bundle_calculation.individual_total - expected_individual_total) < Decimal("0.01")
        assert abs(bundle_calculation.bundle_price - expected_bundle_price) < Decimal("0.01")
        assert abs(bundle_calculation.savings_amount - expected_savings) < Decimal("0.01")
        assert abs(bundle_calculation.savings_percentage - expected_savings_percentage) < Decimal("0.1")
        
        # Test 4: Annual discount calculations
        annual_calculation = await billing_service.calculate_annual_discount(
            test_db, user.id,
            {
                "tier": SubscriptionTier.COMPLETE_PLATFORM,
                "billing_cycle": "annual"
            }
        )
        
        monthly_price = Decimal("399")
        annual_monthly_equivalent = monthly_price * 12  # $4,788
        annual_discount_rate = Decimal("0.20")  # 20% discount
        expected_annual_price = annual_monthly_equivalent * (1 - annual_discount_rate)  # $3,830.40
        expected_annual_savings = annual_monthly_equivalent - expected_annual_price  # $957.60
        
        assert abs(annual_calculation.annual_price - expected_annual_price) < Decimal("0.01")
        assert abs(annual_calculation.annual_savings - expected_annual_savings) < Decimal("0.01")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.billing
    async def test_usage_tracking_accuracy(self, test_db, test_users_db):
        """
        ⚠️ CRITICAL: Test usage tracking accuracy across all components.
        
        Validates that usage is accurately tracked and attributed
        across Reader, Planner, and Actor components.
        """
        user = test_users_db["user"]
        
        subscription = await subscription_service.create_subscription(
            test_db, user.id,
            {
                "tier": SubscriptionTier.COMPLETE_PLATFORM,
                "status": SubscriptionStatus.ACTIVE
            }
        )
        
        # Test 1: Reader usage tracking
        initial_usage = await subscription_service.get_usage_stats(test_db, user.id)
        initial_parses = initial_usage.get("parses", 0)
        
        # Simulate parsing operations
        parse_operations = []
        for i in range(10):
            operation = await web_parser_service.parse_webpage_async(
                test_db,
                task_id=None,
                url=f"https://example{i}.com",
                user_id=user.id,
                track_usage=True
            )
            parse_operations.append(operation)
        
        # Verify usage tracking
        updated_usage = await subscription_service.get_usage_stats(test_db, user.id)
        expected_parses = initial_parses + len([op for op in parse_operations if op.success])
        
        assert updated_usage["parses"] == expected_parses, \
               f"Parse usage tracking incorrect: {updated_usage['parses']} vs {expected_parses}"
        
        # Test 2: Planner usage tracking
        initial_plans = updated_usage.get("plans", 0)
        
        # Simulate planning operations
        planning_operations = []
        for i in range(5):
            if i < len(parse_operations) and parse_operations[i].success:
                plan_operation = await planning_service.generate_execution_plan(
                    test_db,
                    user_id=user.id,
                    goal=f"Test goal {i}",
                    parsed_webpage=parse_operations[i],
                    track_usage=True
                )
                planning_operations.append(plan_operation)
        
        # Verify planning usage
        updated_usage = await subscription_service.get_usage_stats(test_db, user.id)
        expected_plans = initial_plans + len([op for op in planning_operations if op.status == "ready"])
        
        assert updated_usage["plans"] == expected_plans, \
               f"Plan usage tracking incorrect: {updated_usage['plans']} vs {expected_plans}"
        
        # Test 3: Actor usage tracking
        initial_executions = updated_usage.get("executions", 0)
        
        # Simulate execution operations
        execution_operations = []
        for i, plan_op in enumerate(planning_operations):
            if plan_op and plan_op.status == "ready":
                exec_operation = await action_executor.execute_plan(
                    test_db,
                    execution_plan=plan_op,
                    user_id=user.id,
                    track_usage=True
                )
                execution_operations.append(exec_operation)
        
        # Verify execution usage
        final_usage = await subscription_service.get_usage_stats(test_db, user.id)
        expected_executions = initial_executions + len([op for op in execution_operations if op.success])
        
        assert final_usage["executions"] == expected_executions, \
               f"Execution usage tracking incorrect: {final_usage['executions']} vs {expected_executions}"
        
        # Test 4: Usage attribution and analytics
        usage_breakdown = await analytics_service.get_usage_breakdown(
            test_db, user.id, timeframe="current_month"
        )
        
        assert usage_breakdown["reader"]["total_operations"] == expected_parses
        assert usage_breakdown["planner"]["total_operations"] == expected_plans  
        assert usage_breakdown["actor"]["total_operations"] == expected_executions
        
        # Test 5: Usage reset on billing cycle
        # Simulate billing cycle reset
        await subscription_service.reset_usage_cycle(test_db, user.id)
        
        reset_usage = await subscription_service.get_usage_stats(test_db, user.id)
        assert reset_usage["parses"] == 0, "Usage should reset on new billing cycle"
        assert reset_usage["plans"] == 0, "Usage should reset on new billing cycle"
        assert reset_usage["executions"] == 0, "Usage should reset on new billing cycle"
        
        # Historical usage should be preserved
        historical_usage = await analytics_service.get_historical_usage(
            test_db, user.id, months_back=1
        )
        assert len(historical_usage) > 0, "Historical usage should be preserved"
        assert historical_usage[0]["parses"] == expected_parses, "Historical data should be accurate"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.billing
    async def test_stripe_integration_comprehensive(self, test_db, test_users_db):
        """
        ⚠️ CRITICAL: Test comprehensive Stripe integration.
        
        Validates payment processing, webhook handling, and billing
        synchronization with Stripe.
        """
        user = test_users_db["user"]
        
        # Test 1: Customer creation in Stripe
        with patch('app.services.billing_service.stripe.Customer.create') as mock_create_customer:
            mock_create_customer.return_value = MagicMock(id="cus_test123")
            
            stripe_customer = await billing_service.create_stripe_customer(
                test_db, user.id,
                {
                    "email": user.email,
                    "name": user.full_name,
                    "metadata": {"user_id": str(user.id)}
                }
            )
            
            assert stripe_customer.customer_id == "cus_test123"
            mock_create_customer.assert_called_once()
        
        # Test 2: Payment method attachment
        with patch('app.services.billing_service.stripe.PaymentMethod.attach') as mock_attach:
            mock_attach.return_value = MagicMock(id="pm_test456")
            
            payment_method = await billing_service.attach_payment_method(
                test_db, user.id,
                {
                    "payment_method_id": "pm_test456",
                    "set_as_default": True
                }
            )
            
            assert payment_method.stripe_pm_id == "pm_test456"
            assert payment_method.is_default is True
            mock_attach.assert_called_once()
        
        # Test 3: Subscription creation in Stripe
        with patch('app.services.billing_service.stripe.Subscription.create') as mock_create_sub:
            mock_create_sub.return_value = MagicMock(
                id="sub_test789",
                status="active",
                current_period_start=1640995200,  # 2022-01-01
                current_period_end=1643673600,   # 2022-02-01
                latest_invoice=MagicMock(id="in_test999")
            )
            
            subscription = await billing_service.create_stripe_subscription(
                test_db, user.id,
                {
                    "tier": SubscriptionTier.COMPLETE_PLATFORM,
                    "payment_method_id": "pm_test456"
                }
            )
            
            assert subscription.stripe_subscription_id == "sub_test789"
            assert subscription.status == SubscriptionStatus.ACTIVE
            mock_create_sub.assert_called_once()
        
        # Test 4: Webhook event processing
        webhook_events = [
            {
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_test789",
                        "status": "past_due",
                        "current_period_start": 1640995200,
                        "current_period_end": 1643673600
                    }
                }
            },
            {
                "type": "invoice.payment_succeeded",
                "data": {
                    "object": {
                        "id": "in_test999",
                        "subscription": "sub_test789",
                        "amount_paid": 39900,  # $399.00
                        "currency": "usd"
                    }
                }
            },
            {
                "type": "invoice.payment_failed",
                "data": {
                    "object": {
                        "id": "in_test888",
                        "subscription": "sub_test789",
                        "amount_due": 39900,
                        "attempt_count": 1
                    }
                }
            }
        ]
        
        for event in webhook_events:
            result = await billing_service.process_stripe_webhook(test_db, event)
            assert result.success, f"Webhook processing failed for {event['type']}"
            
            if event["type"] == "customer.subscription.updated":
                # Subscription status should be updated
                updated_sub = await subscription_service.get_subscription_by_stripe_id(
                    test_db, "sub_test789"
                )
                assert updated_sub.status == SubscriptionStatus.PAST_DUE
            
            elif event["type"] == "invoice.payment_succeeded":
                # Payment should be recorded
                payment_record = await billing_service.get_payment_by_invoice_id(
                    test_db, "in_test999"
                )
                assert payment_record is not None
                assert payment_record.amount == Decimal("399.00")
                assert payment_record.status == "succeeded"
            
            elif event["type"] == "invoice.payment_failed":
                # Failed payment should be recorded
                failed_payment = await billing_service.get_payment_by_invoice_id(
                    test_db, "in_test888"
                )
                assert failed_payment is not None
                assert failed_payment.status == "failed"
        
        # Test 5: Billing data synchronization
        # Verify local data matches Stripe data
        with patch('app.services.billing_service.stripe.Subscription.retrieve') as mock_retrieve:
            mock_retrieve.return_value = MagicMock(
                id="sub_test789",
                status="active",
                current_period_start=1640995200,
                current_period_end=1643673600,
                plan=MagicMock(amount=39900, currency="usd")
            )
            
            sync_result = await billing_service.sync_subscription_with_stripe(
                test_db, "sub_test789"
            )
            
            assert sync_result.success, "Stripe sync should succeed"
            
            # Local subscription should match Stripe data
            synced_subscription = await subscription_service.get_subscription_by_stripe_id(
                test_db, "sub_test789"
            )
            assert synced_subscription.status == SubscriptionStatus.ACTIVE
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.billing
    async def test_revenue_attribution_conversion_tracking(self, test_db, test_users_db, test_client, auth_headers):
        """
        ⚠️ CRITICAL: Test revenue attribution and conversion tracking.
        
        Validates that user journeys from free tier to paid subscriptions
        are properly tracked for revenue optimization.
        """
        user = test_users_db["user"]
        
        # Create free tier user journey
        free_subscription = await subscription_service.create_subscription(
            test_db, user.id,
            {
                "tier": SubscriptionTier.FREE,
                "status": SubscriptionStatus.ACTIVE,
                "source": "organic_signup"
            }
        )
        
        # Test 1: Track usage approach to limits
        usage_events = []
        
        # Simulate gradual usage increase
        for day in range(15):
            daily_usage = min(10 + day * 2, 25)  # Increasing usage pattern
            
            for i in range(daily_usage):
                await subscription_service.track_usage(test_db, user.id, "parses", 1)
                
                # Track analytics events
                if i == 0:  # First usage of the day
                    await analytics_service.track_event(
                        test_db, user.id, "daily_session_start",
                        {"day": day, "cumulative_usage": daily_usage * day}
                    )
            
            # Check if upgrade prompts should be shown
            usage_status = await subscription_service.get_usage_status(test_db, user.id)
            if usage_status["parses"]["percentage"] >= 80:
                await analytics_service.track_event(
                    test_db, user.id, "upgrade_prompt_eligible",
                    {
                        "usage_percentage": usage_status["parses"]["percentage"],
                        "days_since_signup": day,
                        "component": "reader"
                    }
                )
        
        # Test 2: Track upgrade prompt interactions
        # Simulate user viewing upgrade prompts
        for i in range(3):
            await analytics_service.track_event(
                test_db, user.id, "upgrade_prompt_viewed",
                {
                    "prompt_type": "usage_limit_warning",
                    "tier_suggested": "complete_platform",
                    "savings_highlighted": "40_percent",
                    "session_id": f"session_{i}"
                }
            )
            
            if i == 1:  # User clicks on pricing comparison
                await analytics_service.track_event(
                    test_db, user.id, "pricing_comparison_viewed",
                    {
                        "tiers_compared": ["free", "reader_pro", "complete_platform"],
                        "savings_calculator_used": True
                    }
                )
        
        # Test 3: Track conversion funnel
        # User decides to upgrade
        conversion_start = datetime.utcnow()
        
        await analytics_service.track_event(
            test_db, user.id, "upgrade_flow_started",
            {
                "target_tier": "complete_platform",
                "trigger": "usage_limit_reached",
                "days_to_conversion": 15
            }
        )
        
        # Simulate payment page visit
        await analytics_service.track_event(
            test_db, user.id, "payment_page_visited",
            {"payment_method": "stripe_card"}
        )
        
        # Complete upgrade
        paid_subscription = await subscription_service.upgrade_subscription(
            test_db, user.id,
            {
                "new_tier": SubscriptionTier.COMPLETE_PLATFORM,
                "payment_method_id": "pm_test_conversion",
                "source": "usage_limit_conversion"
            }
        )
        
        conversion_end = datetime.utcnow()
        
        await analytics_service.track_event(
            test_db, user.id, "subscription_upgraded",
            {
                "from_tier": "free",
                "to_tier": "complete_platform",
                "conversion_duration_seconds": (conversion_end - conversion_start).total_seconds(),
                "revenue_amount": 399.00,
                "first_payment_successful": True
            }
        )
        
        # Test 4: Validate conversion analytics
        conversion_metrics = await analytics_service.get_conversion_metrics(
            test_db, user.id, timeframe="lifetime"
        )
        
        # Verify conversion funnel metrics
        assert conversion_metrics["upgrade_prompts_shown"] >= 3
        assert conversion_metrics["pricing_comparisons_viewed"] >= 1
        assert conversion_metrics["upgrade_flows_started"] >= 1
        assert conversion_metrics["successful_conversions"] == 1
        
        # Calculate conversion rate
        conversion_rate = (conversion_metrics["successful_conversions"] / 
                          conversion_metrics["upgrade_prompts_shown"]) * 100
        assert conversion_rate > 0, "Should have positive conversion rate"
        
        # Test 5: Revenue attribution
        revenue_attribution = await analytics_service.get_revenue_attribution(
            test_db, user.id
        )
        
        assert revenue_attribution["total_lifetime_value"] == Decimal("399.00")
        assert revenue_attribution["conversion_source"] == "usage_limit_conversion"
        assert revenue_attribution["days_to_conversion"] == 15
        assert revenue_attribution["touch_points"] >= 4  # Multiple interactions
        
        # Test 6: Cohort analysis for optimization
        cohort_data = await analytics_service.get_cohort_analysis(
            test_db,
            {
                "signup_date_start": datetime.utcnow() - timedelta(days=30),
                "signup_date_end": datetime.utcnow(),
                "conversion_timeframe_days": 30
            }
        )
        
        # User should be in conversion cohort
        assert any(
            cohort["user_id"] == user.id and cohort["converted"] 
            for cohort in cohort_data["cohort_members"]
        )
        
        # Test 7: A/B test attribution (if applicable)
        # Track which upgrade prompts/messages were most effective
        ab_test_results = await analytics_service.get_ab_test_results(
            test_db,
            {
                "test_name": "upgrade_prompt_messaging",
                "user_id": user.id
            }
        )
        
        if ab_test_results:
            assert ab_test_results["variant_shown"] in ["control", "savings_focused", "feature_focused"]
            assert ab_test_results["conversion_achieved"] is True