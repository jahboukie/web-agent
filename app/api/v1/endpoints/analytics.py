"""
Analytics API Endpoints

Revenue-optimized analytics endpoints for WebAgent's 2025 pricing model.
Designed to drive strategic upgrades through intelligent data presentation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import structlog

from app.schemas.analytics import (
    AnalyticsDashboard, UsageMetrics, PlatformAnalytics, UpgradeOpportunity,
    SuccessMetric, UserSubscription, BillingInfo, ComponentMetrics, ROICalculation,
    SubscriptionTier, ComponentType
)
from app.schemas.user import User
from app.api.dependencies import get_async_session, get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.subscription_service import SubscriptionService
from app.services.billing_service import BillingService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
analytics_service = AnalyticsService()
subscription_service = SubscriptionService()
billing_service = BillingService()


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get comprehensive analytics dashboard with revenue optimization.
    
    Returns complete dashboard data including:
    - Usage metrics and trends
    - Platform analytics across all components
    - Strategic upgrade opportunities
    - Success metrics and ROI calculations
    - Billing information and subscription status
    """
    
    try:
        logger.info("Loading analytics dashboard", user_id=current_user.id)
        
        # Get comprehensive dashboard data
        dashboard = await analytics_service.get_dashboard_data(db, current_user.id)
        
        logger.info("Analytics dashboard loaded successfully", 
                   user_id=current_user.id,
                   tier=dashboard.subscription.tier,
                   upgrade_opportunities=len(dashboard.upgrade_opportunities))
        
        return dashboard
        
    except Exception as e:
        logger.error("Failed to load analytics dashboard", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load analytics dashboard"
        )


@router.get("/usage", response_model=UsageMetrics)
async def get_usage_metrics(
    hours: int = Query(default=24, ge=1, le=8760),  # Max 1 year
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed usage metrics for specified time period.
    
    Returns comprehensive usage data including:
    - Current period usage across all components
    - Historical trends and patterns
    - Performance metrics and success rates
    - ROI calculations and value metrics
    """
    
    try:
        usage_metrics = await analytics_service.get_usage_metrics(
            db, current_user.id, hours
        )
        
        return usage_metrics
        
    except Exception as e:
        logger.error("Failed to get usage metrics", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage metrics"
        )


@router.get("/subscription", response_model=UserSubscription)
async def get_subscription_details(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get user's current subscription details and usage status.
    
    Returns subscription information including:
    - Current tier and billing status
    - Usage limits and current consumption
    - Feature access and restrictions
    - Billing cycle and payment information
    """
    
    try:
        subscription = await subscription_service.get_user_subscription(
            db, current_user.id
        )
        
        return subscription
        
    except Exception as e:
        logger.error("Failed to get subscription details", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription details"
        )


@router.get("/upgrade-opportunities", response_model=List[UpgradeOpportunity])
async def get_upgrade_opportunities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get strategic upgrade opportunities for conversion optimization.
    
    Returns personalized upgrade recommendations based on:
    - Current usage patterns and limits
    - Feature utilization and restrictions
    - Cost savings and value propositions
    - Urgency factors and limited-time offers
    """
    
    try:
        opportunities = await analytics_service.get_upgrade_opportunities(
            db, current_user.id
        )
        
        # Sort by priority for maximum conversion impact
        opportunities.sort(key=lambda x: x.priority)
        
        return opportunities
        
    except Exception as e:
        logger.error("Failed to get upgrade opportunities", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve upgrade opportunities"
        )


@router.get("/component/{component_type}", response_model=ComponentMetrics)
async def get_component_metrics(
    component_type: ComponentType,
    hours: int = Query(default=24, ge=1, le=8760),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed metrics for specific AI component.
    
    Returns component-specific analytics including:
    - Usage statistics and performance metrics
    - Success rates and quality scores
    - Trend analysis and benchmarking
    - Component-specific insights
    """
    
    try:
        metrics = await analytics_service.get_component_metrics(
            db, current_user.id, component_type, hours
        )
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get component metrics", 
                    user_id=current_user.id, 
                    component=component_type, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve {component_type} metrics"
        )


@router.get("/roi-calculation", response_model=ROICalculation)
async def get_roi_calculation(
    hourly_rate: float = Query(default=50.0, ge=10.0, le=500.0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Calculate ROI and value demonstration metrics.
    
    Returns comprehensive ROI analysis including:
    - Time saved through automation
    - Labor cost savings calculations
    - Subscription cost vs. value analysis
    - Payback period and annual value
    """
    
    try:
        roi = await analytics_service.calculate_roi(
            db, current_user.id, hourly_rate
        )
        
        return roi
        
    except Exception as e:
        logger.error("Failed to calculate ROI", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate ROI metrics"
        )


@router.get("/success-metrics", response_model=List[SuccessMetric])
async def get_success_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get success metrics for value demonstration.
    
    Returns key success indicators including:
    - Automation success rates
    - Performance improvements
    - User satisfaction scores
    - Benchmark comparisons
    """
    
    try:
        metrics = await analytics_service.get_success_metrics(
            db, current_user.id
        )
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get success metrics", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve success metrics"
        )


@router.get("/billing", response_model=BillingInfo)
async def get_billing_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get comprehensive billing information.
    
    Returns billing details including:
    - Current subscription and payment method
    - Billing history and upcoming charges
    - Account credits and active discounts
    - Invoice and payment records
    """
    
    try:
        billing_info = await billing_service.get_billing_info(
            db, current_user.id
        )
        
        return billing_info
        
    except Exception as e:
        logger.error("Failed to get billing info", 
                    user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve billing information"
        )


@router.post("/track-event")
async def track_analytics_event(
    event_type: str,
    event_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Track analytics events for conversion optimization.
    
    Records user interactions for:
    - Upgrade flow analytics
    - Feature usage tracking
    - Conversion funnel analysis
    - A/B testing and optimization
    """
    
    try:
        await analytics_service.track_event(
            db, current_user.id, event_type, event_data
        )
        
        return {"status": "success", "message": "Event tracked successfully"}
        
    except Exception as e:
        logger.error("Failed to track analytics event", 
                    user_id=current_user.id, 
                    event_type=event_type, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track analytics event"
        )
