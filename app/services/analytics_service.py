"""
Analytics Service

Revenue-optimized analytics service for WebAgent's 2025 pricing model.
Implements intelligent upgrade detection and conversion optimization.
"""

from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_plan import ExecutionPlan
from app.models.task import Task
from app.schemas.analytics import (
    AnalyticsDashboard,
    ComponentMetrics,
    ComponentType,
    ConversionMetrics,
    PlatformAnalytics,
    ROICalculation,
    SubscriptionTier,
    SuccessMetric,
    TrendDirection,
    UpgradeOpportunity,
    UsageMetrics,
)
from app.services.billing_service import BillingService
from app.services.subscription_service import SubscriptionService

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """
    Analytics service for revenue-optimized dashboard and conversion tracking.
    """

    def __init__(self):
        self.subscription_service = SubscriptionService()
        self.billing_service = BillingService()

    async def get_dashboard_data(
        self, db: AsyncSession, user_id: int
    ) -> AnalyticsDashboard:
        """
        Get comprehensive analytics dashboard data with revenue optimization.
        """

        logger.info("Generating analytics dashboard", user_id=user_id)

        # Get user subscription and billing info
        subscription = await self.subscription_service.get_user_subscription(
            db, user_id
        )
        billing_info = await self.billing_service.get_billing_info(db, user_id)

        # Get usage metrics
        usage_metrics = await self.get_usage_metrics(db, user_id, hours=24)

        # Get platform analytics
        platform_analytics = await self.get_platform_analytics(db, user_id)

        # Generate success metrics for value demonstration
        success_metrics = await self.get_success_metrics(db, user_id)

        # Calculate ROI for value proposition
        roi_calculation = await self.calculate_roi(db, user_id)

        # Generate strategic upgrade opportunities
        upgrade_opportunities = await self.get_upgrade_opportunities(db, user_id)

        # Get conversion metrics
        conversion_metrics = await self.get_conversion_metrics(db, user_id)

        # Set cache expiry
        cache_expires_at = datetime.utcnow() + timedelta(minutes=5)

        return AnalyticsDashboard(
            user_id=user_id,
            subscription=subscription,
            usage_metrics=usage_metrics,
            platform_analytics=platform_analytics,
            success_metrics=success_metrics,
            roi_calculation=roi_calculation,
            upgrade_opportunities=upgrade_opportunities,
            conversion_metrics=conversion_metrics,
            billing_info=billing_info,
            cache_expires_at=cache_expires_at,
        )

    async def get_usage_metrics(
        self, db: AsyncSession, user_id: int, hours: int = 24
    ) -> UsageMetrics:
        """
        Get comprehensive usage metrics for the specified time period.
        """

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Get task counts (parsing operations)
        parse_query = select(func.count(Task.id)).where(
            and_(Task.user_id == user_id, Task.created_at >= cutoff_time)
        )
        parses_used = (await db.execute(parse_query)).scalar() or 0

        # Get execution plan counts (planning operations)
        plan_query = select(func.count(ExecutionPlan.id)).where(
            and_(
                ExecutionPlan.user_id == user_id,
                ExecutionPlan.created_at >= cutoff_time,
            )
        )
        plans_used = (await db.execute(plan_query)).scalar() or 0

        # Get execution counts (action operations)
        execution_query = select(func.count(ExecutionPlan.id)).where(
            and_(
                ExecutionPlan.user_id == user_id,
                ExecutionPlan.status == "completed",
                ExecutionPlan.created_at >= cutoff_time,
            )
        )
        executions_used = (await db.execute(execution_query)).scalar() or 0

        # Calculate success rates
        total_tasks = (
            await db.execute(select(func.count(Task.id)).where(Task.user_id == user_id))
        ).scalar() or 0

        successful_tasks = (
            await db.execute(
                select(func.count(Task.id)).where(
                    and_(Task.user_id == user_id, Task.status == "completed")
                )
            )
        ).scalar() or 0

        parse_success_rate = (
            (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

        # Generate trend data
        daily_usage = await self._generate_daily_usage_trend(db, user_id, hours)

        # Calculate performance metrics
        avg_parse_time = await self._calculate_avg_parse_time(db, user_id)
        avg_plan_time = await self._calculate_avg_plan_time(db, user_id)
        avg_execution_time = await self._calculate_avg_execution_time(db, user_id)

        # Calculate ROI metrics
        time_saved_hours = parses_used * 0.5 + plans_used * 1.0 + executions_used * 2.0
        cost_saved_usd = time_saved_hours * 50.0  # Assume $50/hour
        automation_value = cost_saved_usd * 1.2  # 20% efficiency bonus

        return UsageMetrics(
            parses_used=parses_used,
            plans_used=plans_used,
            executions_used=executions_used,
            api_calls_used=parses_used + plans_used + executions_used,
            storage_used_gb=0.1 * (parses_used + plans_used),  # Estimate
            daily_usage=daily_usage,
            weekly_trends=[],
            monthly_summary={},
            avg_parse_time_ms=avg_parse_time,
            avg_plan_time_ms=avg_plan_time,
            avg_execution_time_ms=avg_execution_time,
            parse_success_rate=parse_success_rate,
            plan_success_rate=85.0,  # Default high success rate
            execution_success_rate=90.0,  # Default high success rate
            time_saved_hours=time_saved_hours,
            cost_saved_usd=cost_saved_usd,
            automation_value=automation_value,
        )

    async def get_upgrade_opportunities(
        self, db: AsyncSession, user_id: int
    ) -> list[UpgradeOpportunity]:
        """
        Generate strategic upgrade opportunities for conversion optimization.
        """

        opportunities = []
        subscription = await self.subscription_service.get_user_subscription(
            db, user_id
        )
        usage_metrics = await self.get_usage_metrics(db, user_id, hours=720)  # 30 days

        # Usage-based upgrade opportunities
        if subscription.tier == SubscriptionTier.FREE:
            # Check if approaching limits
            parse_usage_pct = (usage_metrics.parses_used / 200) * 100
            plan_usage_pct = (usage_metrics.plans_used / 20) * 100
            execution_usage_pct = (usage_metrics.executions_used / 10) * 100

            if parse_usage_pct > 80:
                opportunities.append(
                    UpgradeOpportunity(
                        type="usage_limit",
                        priority=1,
                        title="Reader Usage Approaching Limit",
                        description=f"You've used {usage_metrics.parses_used}/200 website parses this month",
                        value_proposition="Upgrade to Reader Pro for unlimited parsing + advanced analytics",
                        current_tier=subscription.tier,
                        recommended_tier=SubscriptionTier.READER_PRO,
                        savings_amount=0,
                        savings_percentage=0,
                        cta_text="Upgrade to Reader Pro - $129/mo",
                        usage_percentage=parse_usage_pct,
                        days_until_limit=max(
                            1,
                            int(
                                (200 - usage_metrics.parses_used)
                                / max(1, usage_metrics.parses_used / 30)
                            ),
                        ),
                    )
                )

            # Bundle savings opportunity
            if parse_usage_pct > 60 and plan_usage_pct > 60:
                opportunities.append(
                    UpgradeOpportunity(
                        type="savings",
                        priority=2,
                        title="Complete Platform - 40% Savings",
                        description="You're using multiple AI components - save with our bundle",
                        value_proposition="Get Reader + Planner + Actor for $399/mo (save $138/mo vs individual)",
                        current_tier=subscription.tier,
                        recommended_tier=SubscriptionTier.COMPLETE_PLATFORM,
                        savings_amount=138,
                        savings_percentage=40,
                        cta_text="Save $138/mo with Complete Platform",
                        usage_percentage=max(parse_usage_pct, plan_usage_pct),
                    )
                )

        # Feature unlock opportunities
        if subscription.tier in [SubscriptionTier.FREE, SubscriptionTier.READER_PRO]:
            opportunities.append(
                UpgradeOpportunity(
                    type="feature_unlock",
                    priority=3,
                    title="Unlock AI Planning Intelligence",
                    description="Transform goals into executable plans with our AI Brain",
                    value_proposition="Enterprise customers achieve 3x automation ROI with AI planning",
                    current_tier=subscription.tier,
                    recommended_tier=SubscriptionTier.PLANNER_PRO,
                    cta_text="Unlock AI Planning - $179/mo",
                )
            )

        # Performance boost opportunities
        if usage_metrics.avg_parse_time_ms > 5000:  # Slow performance
            opportunities.append(
                UpgradeOpportunity(
                    type="performance_boost",
                    priority=4,
                    title="Priority Processing Available",
                    description="Reduce wait times with priority queue access",
                    value_proposition="Pro users get 3x faster processing and priority support",
                    current_tier=subscription.tier,
                    recommended_tier=SubscriptionTier.COMPLETE_PLATFORM,
                    cta_text="Get Priority Processing",
                )
            )

        return opportunities

    async def get_success_metrics(
        self, db: AsyncSession, user_id: int
    ) -> list[SuccessMetric]:
        """
        Generate success metrics for value demonstration.
        """

        usage_metrics = await self.get_usage_metrics(db, user_id)

        metrics = [
            SuccessMetric(
                label="Automation Success Rate",
                value=f"{usage_metrics.parse_success_rate:.1f}%",
                trend=2.5,
                trend_direction=TrendDirection.UP,
                benchmark="Industry avg: 73%",
                tooltip="Percentage of successful automation tasks",
            ),
            SuccessMetric(
                label="Time Saved This Month",
                value=f"{usage_metrics.time_saved_hours:.1f} hours",
                trend=15.2,
                trend_direction=TrendDirection.UP,
                benchmark="Pro users avg: 45 hours",
                tooltip="Total time saved through automation",
            ),
            SuccessMetric(
                label="Cost Savings",
                value=f"${usage_metrics.cost_saved_usd:.0f}",
                trend=8.7,
                trend_direction=TrendDirection.UP,
                benchmark="Enterprise avg: $2,400",
                tooltip="Estimated labor cost savings",
            ),
            SuccessMetric(
                label="Automation Value",
                value=f"${usage_metrics.automation_value:.0f}",
                trend=12.3,
                trend_direction=TrendDirection.UP,
                benchmark="Complete Platform avg: $3,200",
                tooltip="Total value generated through automation",
            ),
        ]

        return metrics

    async def calculate_roi(
        self, db: AsyncSession, user_id: int, hourly_rate: float = 50.0
    ) -> ROICalculation:
        """
        Calculate comprehensive ROI metrics for value demonstration.
        """

        usage_metrics = await self.get_usage_metrics(db, user_id, hours=720)  # 30 days
        subscription = await self.subscription_service.get_user_subscription(
            db, user_id
        )

        # Calculate time saved
        time_saved_hours = usage_metrics.time_saved_hours

        # Calculate cost savings
        labor_cost_saved = time_saved_hours * hourly_rate

        # Get subscription cost
        subscription_cost = subscription.monthly_cost

        # Calculate net savings and ROI
        net_savings = labor_cost_saved - subscription_cost
        roi_percentage = (
            (net_savings / max(subscription_cost, 1)) * 100
            if subscription_cost > 0
            else 0
        )

        # Calculate payback period
        daily_savings = labor_cost_saved / 30
        payback_period_days = (
            int(subscription_cost / max(daily_savings, 1)) if daily_savings > 0 else 0
        )

        # Annual value projection
        annual_value = net_savings * 12

        return ROICalculation(
            time_saved_hours=time_saved_hours,
            hourly_rate_usd=hourly_rate,
            labor_cost_saved=labor_cost_saved,
            subscription_cost=subscription_cost,
            net_savings=net_savings,
            roi_percentage=roi_percentage,
            payback_period_days=payback_period_days,
            annual_value=annual_value,
        )

    async def _generate_daily_usage_trend(
        self, db: AsyncSession, user_id: int, hours: int
    ) -> list[dict[str, Any]]:
        """Generate daily usage trend data."""
        # Implementation would query database for daily usage patterns
        # For now, return sample data
        return [
            {"date": "2025-06-19", "parses": 15, "plans": 3, "executions": 2},
            {"date": "2025-06-20", "parses": 22, "plans": 5, "executions": 4},
        ]

    async def _calculate_avg_parse_time(self, db: AsyncSession, user_id: int) -> float:
        """Calculate average parsing time."""
        # Implementation would calculate from task execution times
        return 2500.0  # Sample: 2.5 seconds

    async def _calculate_avg_plan_time(self, db: AsyncSession, user_id: int) -> float:
        """Calculate average planning time."""
        return 8500.0  # Sample: 8.5 seconds

    async def _calculate_avg_execution_time(
        self, db: AsyncSession, user_id: int
    ) -> float:
        """Calculate average execution time."""
        return 15000.0  # Sample: 15 seconds

    async def get_platform_analytics(
        self, db: AsyncSession, user_id: int
    ) -> PlatformAnalytics:
        """Get comprehensive platform analytics."""
        # Implementation would aggregate metrics across all components

        reader_metrics = ComponentMetrics(
            component=ComponentType.READER,
            total_requests=100,
            successful_requests=95,
            success_rate=95.0,
            avg_response_time_ms=2500.0,
        )

        planner_metrics = ComponentMetrics(
            component=ComponentType.PLANNER,
            total_requests=50,
            successful_requests=47,
            success_rate=94.0,
            avg_response_time_ms=8500.0,
        )

        actor_metrics = ComponentMetrics(
            component=ComponentType.ACTOR,
            total_requests=25,
            successful_requests=23,
            success_rate=92.0,
            avg_response_time_ms=15000.0,
        )

        unified_metrics = ComponentMetrics(
            component=ComponentType.UNIFIED,
            total_requests=25,
            successful_requests=22,
            success_rate=88.0,
            avg_response_time_ms=26000.0,
        )

        return PlatformAnalytics(
            reader_metrics=reader_metrics,
            planner_metrics=planner_metrics,
            actor_metrics=actor_metrics,
            unified_metrics=unified_metrics,
            workflow_success_rate=88.0,
            end_to_end_performance=85.0,
            integration_health=92.0,
            feature_adoption_rates={
                "reader": 0.95,
                "planner": 0.75,
                "actor": 0.45,
                "unified": 0.35,
            },
            user_journey_analytics={},
            engagement_metrics={},
        )

    async def get_conversion_metrics(
        self, db: AsyncSession, user_id: int
    ) -> ConversionMetrics:
        """Get conversion optimization metrics."""

        return ConversionMetrics(
            usage_based_upgrades=0,
            feature_based_upgrades=0,
            savings_based_upgrades=0,
            individual_to_bundle_rate=0.55,
            bundle_to_enterprise_rate=0.25,
            addon_attachment_rate=0.40,
            demo_to_conversion_rate=0.35,
            trial_engagement_score=0.75,
        )

    async def get_component_metrics(
        self, db: AsyncSession, user_id: int, component_type: ComponentType, hours: int
    ) -> ComponentMetrics:
        """Get detailed metrics for specific component."""
        # Implementation would query component-specific metrics
        return ComponentMetrics(
            component=component_type,
            total_requests=100,
            successful_requests=95,
            success_rate=95.0,
            avg_response_time_ms=2500.0,
            accuracy_score=0.92,
            confidence_score=0.88,
            user_satisfaction=0.91,
        )

    async def track_event(
        self, db: AsyncSession, user_id: int, event_type: str, event_data: dict
    ):
        """Track analytics events for conversion optimization."""
        logger.info(
            "Tracking analytics event",
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
        )
        # Implementation would store event in analytics database
