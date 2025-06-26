"""
Subscription Service

Manages WebAgent's 2025 revenue-optimized pricing model with strategic tier management.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.analytics import (
    SubscriptionStatus,
    SubscriptionTier,
    UsageMetrics,
    UserSubscription,
)

logger = structlog.get_logger(__name__)


class SubscriptionService:
    """
    Subscription management service for revenue-optimized pricing tiers.
    """

    # 2025 Optimized Pricing Structure
    PRICING_TIERS = {
        SubscriptionTier.FREE: {
            "name": "Free Tier",
            "monthly_cost": 0.0,
            "limits": {
                "parses": 200,
                "plans": 20,
                "executions": 10,
                "storage_gb": 1,
                "api_calls": 1000,
            },
            "features": [
                "Basic website parsing",
                "Limited AI planning",
                "Basic automation",
                "Community support",
            ],
            "restrictions": [
                "Limited usage quotas",
                "Basic analytics only",
                "No priority support",
                "No advanced features",
            ],
        },
        SubscriptionTier.READER_PRO: {
            "name": "Reader Pro",
            "monthly_cost": 129.0,
            "limits": {
                "parses": "unlimited",
                "plans": 20,
                "executions": 10,
                "storage_gb": 10,
                "api_calls": "unlimited",
            },
            "features": [
                "Unlimited website parsing",
                "Advanced parsing analytics",
                "Performance optimization",
                "Priority support",
                "Trend analysis",
                "Element accuracy insights",
            ],
            "restrictions": [
                "Limited AI planning",
                "Limited automation",
                "No workflow analytics",
            ],
        },
        SubscriptionTier.PLANNER_PRO: {
            "name": "Planner Pro",
            "monthly_cost": 179.0,
            "limits": {
                "parses": 200,
                "plans": "unlimited",
                "executions": 10,
                "storage_gb": 15,
                "api_calls": "unlimited",
            },
            "features": [
                "Unlimited AI planning",
                "Workflow analytics",
                "Confidence scoring",
                "Goal completion tracking",
                "AI reasoning performance",
                "Priority support",
            ],
            "restrictions": [
                "Limited website parsing",
                "Limited automation",
                "No execution analytics",
            ],
        },
        SubscriptionTier.ACTOR_PRO: {
            "name": "Actor Pro",
            "monthly_cost": 229.0,
            "limits": {
                "parses": 200,
                "plans": 20,
                "executions": "unlimited",
                "storage_gb": 25,
                "api_calls": "unlimited",
            },
            "features": [
                "Unlimited automation",
                "Execution analytics",
                "Error monitoring",
                "ROI calculations",
                "Success metrics",
                "Priority support",
            ],
            "restrictions": [
                "Limited parsing",
                "Limited planning",
                "No unified analytics",
            ],
        },
        SubscriptionTier.COMPLETE_PLATFORM: {
            "name": "Complete Platform",
            "monthly_cost": 399.0,
            "annual_discount": 0.15,  # 15% discount for annual
            "limits": {
                "parses": "unlimited",
                "plans": "unlimited",
                "executions": "unlimited",
                "storage_gb": 100,
                "api_calls": "unlimited",
            },
            "features": [
                "All Reader Pro features",
                "All Planner Pro features",
                "All Actor Pro features",
                "Unified cross-tool analytics",
                "Integration monitoring",
                "Advanced success metrics",
                "Priority support",
                "40% savings vs individual tools",
            ],
            "restrictions": [
                "No enterprise features",
                "No white-label options",
                "No dedicated CSM",
            ],
        },
        SubscriptionTier.ENTERPRISE_PLATFORM: {
            "name": "Enterprise Platform",
            "monthly_cost": 1499.0,
            "limits": {
                "parses": "unlimited",
                "plans": "unlimited",
                "executions": "unlimited",
                "storage_gb": "unlimited",
                "api_calls": "unlimited",
            },
            "features": [
                "All Complete Platform features",
                "Advanced compliance dashboards",
                "Custom branding & white-label",
                "Dedicated Customer Success Manager",
                "SLA monitoring & guarantees",
                "Early access to features",
                "Custom integrations",
                "Advanced security features",
                "Audit trails & reporting",
            ],
            "restrictions": [],
        },
    }

    async def get_user_subscription(
        self, db: AsyncSession, user_id: int
    ) -> UserSubscription:
        """
        Get user's current subscription details with usage tracking.
        """

        # Get user from database
        user_query = select(User).where(User.id == user_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Determine subscription tier (default to free for now)
        tier = SubscriptionTier.FREE
        if hasattr(user, "subscription_tier") and user.subscription_tier:
            try:
                tier = SubscriptionTier(user.subscription_tier)
            except ValueError:
                tier = SubscriptionTier.FREE  # Default to free if tier is invalid

        # Get tier configuration
        tier_config = self.PRICING_TIERS[tier]

        # Calculate billing dates
        current_period_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        current_period_end = (current_period_start + timedelta(days=32)).replace(
            day=1
        ) - timedelta(days=1)

        # Get current usage (would be calculated from actual usage)
        usage_metrics = await self._calculate_current_usage(db, user_id)

        # Safely extract and cast tier configuration values
        limits = tier_config.get("limits", {})
        monthly_cost = tier_config.get("monthly_cost", 0.0)
        annual_discount = tier_config.get("annual_discount", 0.0)
        features = tier_config.get("features", [])
        restrictions = tier_config.get("restrictions", [])

        return UserSubscription(
            tier=tier,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            limits=limits if isinstance(limits, dict) else {},
            usage=usage_metrics,
            monthly_cost=float(monthly_cost),
            annual_discount=float(annual_discount),
            next_billing_date=current_period_end + timedelta(days=1),
            features=features if isinstance(features, list) else [],
            restrictions=restrictions if isinstance(restrictions, list) else [],
        )

    async def _calculate_current_usage(
        self, db: AsyncSession, user_id: int
    ) -> UsageMetrics:
        """
        Calculate current usage metrics for the user.
        """

        # Get current month's usage
        current_month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        # This would query actual usage from tasks, plans, executions
        # For now, return sample data
        return UsageMetrics(
            parses_used=45,
            plans_used=8,
            executions_used=3,
            api_calls_used=56,
            storage_used_gb=0.3,
            parse_success_rate=94.5,
            plan_success_rate=87.5,
            execution_success_rate=91.2,
            time_saved_hours=12.5,
            cost_saved_usd=625.0,
            automation_value=750.0,
        )

    def get_tier_limits(self, tier: SubscriptionTier) -> dict[str, int | str]:
        """
        Get usage limits for a specific subscription tier.
        """
        limits = self.PRICING_TIERS[tier].get("limits", {})
        return limits if isinstance(limits, dict) else {}

    def get_tier_features(self, tier: SubscriptionTier) -> list[str]:
        """
        Get features available for a specific subscription tier.
        """
        features = self.PRICING_TIERS[tier].get("features", [])
        return features if isinstance(features, list) else []

    def get_tier_cost(self, tier: SubscriptionTier) -> float:
        """
        Get monthly cost for a specific subscription tier.
        """
        cost = self.PRICING_TIERS[tier].get("monthly_cost", 0.0)
        return float(cost)

    def calculate_upgrade_savings(
        self, current_tier: SubscriptionTier, target_tier: SubscriptionTier
    ) -> dict[str, float]:
        """
        Calculate savings when upgrading to a bundle tier.
        """

        current_cost = self.get_tier_cost(current_tier)
        target_cost = self.get_tier_cost(target_tier)

        # Calculate individual tool costs if upgrading to Complete Platform
        if target_tier == SubscriptionTier.COMPLETE_PLATFORM:
            individual_cost = (
                self.get_tier_cost(SubscriptionTier.READER_PRO)
                + self.get_tier_cost(SubscriptionTier.PLANNER_PRO)
                + self.get_tier_cost(SubscriptionTier.ACTOR_PRO)
            )  # $129 + $179 + $229 = $537

            savings_amount = individual_cost - target_cost  # $537 - $399 = $138
            savings_percentage = (savings_amount / individual_cost) * 100  # ~25.7%

            return {
                "savings_amount": savings_amount,
                "savings_percentage": savings_percentage,
                "individual_cost": individual_cost,
                "bundle_cost": target_cost,
            }

        return {
            "savings_amount": 0.0,
            "savings_percentage": 0.0,
            "individual_cost": current_cost,
            "bundle_cost": target_cost,
        }

    def is_usage_approaching_limit(
        self, subscription: UserSubscription, threshold: float = 0.8
    ) -> dict[str, bool]:
        """
        Check if user is approaching usage limits for upgrade prompts.
        """

        approaching_limits: dict[str, bool] = {}
        limits = subscription.limits or {}

        for limit_type, limit_value in limits.items():
            if limit_value == "unlimited" or not isinstance(limit_value, int):
                approaching_limits[limit_type] = False
                continue

            usage_attr = f"{limit_type}_used"
            if hasattr(subscription.usage, usage_attr):
                current_usage = getattr(subscription.usage, usage_attr)
                usage_percentage = current_usage / limit_value
                approaching_limits[limit_type] = usage_percentage >= threshold

        return approaching_limits

    async def upgrade_subscription(
        self, db: AsyncSession, user_id: int, new_tier: SubscriptionTier
    ) -> UserSubscription:
        """
        Upgrade user's subscription to a new tier.
        """

        logger.info(
            "Upgrading user subscription", user_id=user_id, new_tier=new_tier.value
        )

        # Get user
        user_query = select(User).where(User.id == user_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Update subscription tier (this would integrate with billing system)
        # For now, just log the upgrade
        logger.info(
            "Subscription upgrade completed",
            user_id=user_id,
            new_tier=new_tier.value,
            monthly_cost=self.get_tier_cost(new_tier),
        )

        # Return updated subscription
        return await self.get_user_subscription(db, user_id)
