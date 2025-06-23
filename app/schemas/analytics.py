"""
Analytics and Subscription Schemas

Revenue-optimized analytics schemas for WebAgent's 2025 pricing model.
Designed to maximize conversion through strategic feature gating and value demonstration.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


class SubscriptionTier(str, Enum):
    """Subscription tiers with strategic pricing optimization."""

    FREE = "free"
    READER_PRO = "reader_pro"
    PLANNER_PRO = "planner_pro"
    ACTOR_PRO = "actor_pro"
    COMPLETE_PLATFORM = "complete_platform"
    ENTERPRISE_PLATFORM = "enterprise_platform"


class SubscriptionStatus(str, Enum):
    """Subscription status for billing management."""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"


class ComponentType(str, Enum):
    """WebAgent AI components for analytics tracking."""

    READER = "reader"
    PLANNER = "planner"
    ACTOR = "actor"
    UNIFIED = "unified"


class TrendDirection(str, Enum):
    """Trend direction for metrics visualization."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class UsageMetrics(BaseModel):
    """Comprehensive usage metrics across all platform components."""

    # Current period usage
    parses_used: int = 0
    plans_used: int = 0
    executions_used: int = 0
    api_calls_used: int = 0
    storage_used_gb: float = 0.0

    # Historical data for trends
    daily_usage: list[dict[str, Any]] = []
    weekly_trends: list[dict[str, Any]] = []
    monthly_summary: dict[str, Any] = {}

    # Performance metrics
    avg_parse_time_ms: float = 0.0
    avg_plan_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0

    # Success rates
    parse_success_rate: float = 0.0
    plan_success_rate: float = 0.0
    execution_success_rate: float = 0.0

    # ROI metrics
    time_saved_hours: float = 0.0
    cost_saved_usd: float = 0.0
    automation_value: float = 0.0


class UserSubscription(BaseModel):
    """User subscription details with billing integration."""

    tier: SubscriptionTier
    status: SubscriptionStatus

    # Billing cycle
    current_period_start: datetime
    current_period_end: datetime
    trial_end: datetime | None = None

    # Usage limits
    limits: dict[str, int | str] = {
        "parses": 200,
        "plans": 20,
        "executions": 10,
        "storage_gb": 1,
        "api_calls": 1000,
    }

    # Current usage
    usage: UsageMetrics

    # Billing information
    monthly_cost: float = 0.0
    annual_discount: float = 0.0
    next_billing_date: datetime | None = None

    # Feature access
    features: list[str] = []
    restrictions: list[str] = []


class ComponentMetrics(BaseModel):
    """Detailed metrics for individual AI components."""

    component: ComponentType

    # Usage statistics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 0.0

    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Quality metrics
    accuracy_score: float = 0.0
    confidence_score: float = 0.0
    user_satisfaction: float = 0.0

    # Trend data
    performance_trend: list[dict[str, Any]] = []
    usage_trend: list[dict[str, Any]] = []

    # Component-specific metrics
    specific_metrics: dict[str, Any] = {}


class SuccessMetric(BaseModel):
    """Success metrics for value demonstration."""

    label: str
    value: str
    trend: float = 0.0
    trend_direction: TrendDirection = TrendDirection.STABLE
    benchmark: str | None = None
    tooltip: str | None = None

    # Revenue optimization
    upgrade_trigger: bool = False
    upgrade_message: str | None = None


class UpgradeOpportunity(BaseModel):
    """Strategic upgrade opportunities for conversion optimization."""

    type: str  # "usage_limit", "feature_unlock", "performance_boost", "savings"
    priority: int = Field(ge=1, le=5)  # 1 = highest priority

    title: str
    description: str
    value_proposition: str

    # Conversion optimization
    current_tier: SubscriptionTier
    recommended_tier: SubscriptionTier
    savings_amount: float = 0.0
    savings_percentage: float = 0.0

    # Call to action
    cta_text: str = "Upgrade Now"
    cta_url: str = "/billing/upgrade"

    # Urgency factors
    usage_percentage: float = 0.0
    days_until_limit: int | None = None
    limited_time_offer: bool = False


class ROICalculation(BaseModel):
    """ROI calculations for value demonstration."""

    time_saved_hours: float = 0.0
    hourly_rate_usd: float = 50.0  # Default assumption
    labor_cost_saved: float = 0.0

    subscription_cost: float = 0.0
    net_savings: float = 0.0
    roi_percentage: float = 0.0

    payback_period_days: int = 0
    annual_value: float = 0.0


class RevenueMetrics(BaseModel):
    """Revenue and conversion metrics for business intelligence."""

    # Conversion funnel
    free_users: int = 0
    trial_users: int = 0
    paid_users: int = 0

    # Conversion rates
    free_to_trial_rate: float = 0.0
    trial_to_paid_rate: float = 0.0
    free_to_paid_rate: float = 0.0

    # Revenue metrics
    monthly_recurring_revenue: float = 0.0
    annual_recurring_revenue: float = 0.0
    average_revenue_per_user: float = 0.0

    # Churn and retention
    churn_rate: float = 0.0
    retention_rate: float = 0.0
    customer_lifetime_value: float = 0.0


class ConversionMetrics(BaseModel):
    """Conversion optimization metrics."""

    # Upgrade triggers
    usage_based_upgrades: int = 0
    feature_based_upgrades: int = 0
    savings_based_upgrades: int = 0

    # Conversion paths
    individual_to_bundle_rate: float = 0.0
    bundle_to_enterprise_rate: float = 0.0
    addon_attachment_rate: float = 0.0

    # Success factors
    demo_to_conversion_rate: float = 0.0
    trial_engagement_score: float = 0.0


class PlatformAnalytics(BaseModel):
    """Comprehensive platform analytics dashboard."""

    # Component metrics
    reader_metrics: ComponentMetrics
    planner_metrics: ComponentMetrics
    actor_metrics: ComponentMetrics
    unified_metrics: ComponentMetrics

    # Cross-component insights
    workflow_success_rate: float = 0.0
    end_to_end_performance: float = 0.0
    integration_health: float = 0.0

    # User behavior
    feature_adoption_rates: dict[str, float] = {}
    user_journey_analytics: dict[str, Any] = {}
    engagement_metrics: dict[str, float] = {}


class BillingInfo(BaseModel):
    """Billing and payment information."""

    # Current subscription
    subscription: UserSubscription

    # Payment method
    payment_method_type: str | None = None
    last_four_digits: str | None = None

    # Billing history
    recent_invoices: list[dict[str, Any]] = []
    payment_history: list[dict[str, Any]] = []

    # Upcoming charges
    next_charge_amount: float = 0.0
    next_charge_date: datetime | None = None

    # Credits and discounts
    account_credits: float = 0.0
    active_discounts: list[dict[str, str]] = []


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard data structure."""

    # User context
    user_id: int
    subscription: UserSubscription

    # Core metrics
    usage_metrics: UsageMetrics
    platform_analytics: PlatformAnalytics

    # Success demonstration
    success_metrics: list[SuccessMetric]
    roi_calculation: ROICalculation

    # Revenue optimization
    upgrade_opportunities: list[UpgradeOpportunity]
    conversion_metrics: ConversionMetrics

    # Billing integration
    billing_info: BillingInfo

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cache_expires_at: datetime

    @validator("cache_expires_at", pre=True, always=True)
    def set_cache_expiry(cls, v, values):
        if v is None:
            # Cache for 5 minutes for real-time feel
            from datetime import timedelta

            return datetime.utcnow() + timedelta(minutes=5)
        return v
