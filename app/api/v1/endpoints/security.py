"""
Security Management API Endpoints

Provides API endpoints for Zero Trust policy management, trust score monitoring,
and SIEM configuration management.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.api.dependencies import get_current_user, get_db
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.user import AccessContext, DeviceInfo, ZeroTrustVerification
from app.security.zero_trust import zero_trust_engine, TrustAssessment, ZeroTrustPolicy
from app.security.siem_integration import siem_orchestrator, SIEMResponse
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter()


@router.post("/zero-trust/assess", response_model=Dict[str, Any])
async def assess_trust_score(
    access_context: AccessContext,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate Zero Trust assessment for current access context.
    
    Provides comprehensive trust score calculation including:
    - Device trust assessment
    - Location analysis
    - Behavioral patterns
    - Network reputation
    - Authentication factors
    """
    
    try:
        if not settings.ENABLE_ZERO_TRUST:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Zero Trust framework is disabled"
            )
        
        # Calculate trust assessment
        assessment = await zero_trust_engine.calculate_trust_score(
            current_user.id, access_context
        )
        
        # Convert to API response format
        response = {
            "assessment_id": assessment.assessment_id,
            "user_id": assessment.user_id,
            "timestamp": assessment.timestamp.isoformat(),
            "trust_score": assessment.trust_score,
            "trust_level": assessment.trust_level.value,
            "risk_score": assessment.risk_score,
            "confidence_score": assessment.confidence_score,
            "trust_factors": {
                "authentication_strength": assessment.trust_factors.authentication_strength,
                "device_trust_score": assessment.trust_factors.device_trust_score,
                "location_trust_score": assessment.trust_factors.location_trust_score,
                "behavioral_trust_score": assessment.trust_factors.behavioral_trust_score,
                "network_trust_score": assessment.trust_factors.network_trust_score
            },
            "risk_factors": [factor.value for factor in assessment.risk_factors],
            "required_actions": assessment.required_actions,
            "session_restrictions": assessment.session_restrictions,
            "next_verification_in": assessment.next_verification_in
        }
        
        logger.info(
            "Zero Trust assessment completed",
            user_id=current_user.id,
            trust_score=assessment.trust_score,
            trust_level=assessment.trust_level.value
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Zero Trust assessment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trust assessment failed: {str(e)}"
        )


@router.get("/zero-trust/policies", response_model=List[Dict[str, Any]])
async def get_zero_trust_policies(
    current_user: User = Depends(get_current_user)
):
    """Get available Zero Trust policies and their requirements."""
    
    try:
        policies = []
        
        for policy in ZeroTrustPolicy:
            policy_info = {
                "policy_id": policy.value,
                "name": policy.value.replace("_", " ").title(),
                "description": f"Zero Trust policy for {policy.value.replace('_', ' ')}",
                "trust_requirements": {
                    ZeroTrustPolicy.CRITICAL_SYSTEMS: {"min_trust_score": 0.99, "required_mfa": True, "device_managed": True},
                    ZeroTrustPolicy.SENSITIVE_DATA: {"min_trust_score": 0.80, "required_mfa": True, "device_registered": True},
                    ZeroTrustPolicy.STANDARD_ACCESS: {"min_trust_score": 0.60, "required_mfa": False, "device_registered": False},
                    ZeroTrustPolicy.PUBLIC_ACCESS: {"min_trust_score": 0.30, "required_mfa": False, "device_registered": False}
                }.get(policy, {"min_trust_score": 0.60})
            }
            policies.append(policy_info)
        
        return policies
        
    except Exception as e:
        logger.error(f"Failed to get Zero Trust policies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Zero Trust policies"
        )


@router.get("/zero-trust/user-history", response_model=List[Dict[str, Any]])
async def get_user_trust_history(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user)
):
    """Get user's trust score history over specified time period."""
    
    try:
        # This would query the database for historical trust assessments
        # For now, return mock data structure
        history = []
        
        # Generate sample history data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # In production, this would query actual assessment history
        sample_entry = {
            "timestamp": end_date.isoformat(),
            "trust_score": 0.85,
            "trust_level": "high",
            "risk_factors": [],
            "location": "San Francisco, CA",
            "device_type": "desktop"
        }
        
        history.append(sample_entry)
        
        return history
        
    except Exception as e:
        logger.error(f"Failed to get user trust history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trust history"
        )


@router.get("/siem/status", response_model=Dict[str, Any])
async def get_siem_status(
    current_user: User = Depends(get_current_user)
):
    """Get status of all configured SIEM providers."""
    
    try:
        if not settings.ENABLE_SIEM_INTEGRATION:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SIEM integration is disabled"
            )
        
        # Get provider status from SIEM orchestrator
        provider_status = await siem_orchestrator.get_provider_status()
        
        # Add configuration summary
        response = {
            "siem_enabled": settings.ENABLE_SIEM_INTEGRATION,
            "providers_configured": len(provider_status),
            "providers": provider_status,
            "configuration": {
                "batch_size": settings.SIEM_BATCH_SIZE,
                "batch_timeout": settings.SIEM_BATCH_TIMEOUT,
                "retry_attempts": settings.SIEM_RETRY_ATTEMPTS,
                "primary_provider": settings.SIEM_PROVIDER
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get SIEM status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve SIEM status: {str(e)}"
        )


@router.post("/siem/test-event", response_model=List[Dict[str, Any]])
async def send_test_siem_event(
    event_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Send a test event to all configured SIEM providers."""
    
    try:
        if not settings.ENABLE_SIEM_INTEGRATION:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SIEM integration is disabled"
            )
        
        # Create test security event
        from app.schemas.user import SecurityEvent, ThreatLevel
        
        test_event = SecurityEvent(
            event_id=f"test_{datetime.utcnow().timestamp()}",
            event_type="api_test",
            severity=ThreatLevel.LOW,
            user_id=current_user.id,
            source_ip=event_data.get("source_ip", "127.0.0.1"),
            user_agent=event_data.get("user_agent", "WebAgent-API-Test"),
            description="Test event from WebAgent API",
            threat_indicators=[],
            mitigated=False,
            created_at=datetime.utcnow()
        )
        
        # Send to SIEM providers
        responses = await siem_orchestrator.send_security_event(test_event)
        
        # Format responses for API
        formatted_responses = []
        for response in responses:
            formatted_responses.append({
                "success": response.success,
                "status_code": response.status_code,
                "message": response.message,
                "event_id": response.event_id,
                "response_time_ms": response.response_time_ms,
                "error_details": response.error_details
            })
        
        logger.info(f"Test SIEM event sent by user {current_user.id}")
        return formatted_responses
        
    except Exception as e:
        logger.error(f"Failed to send test SIEM event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test event: {str(e)}"
        )


@router.get("/siem/search", response_model=List[Dict[str, Any]])
async def search_siem_events(
    query: str = Query(..., description="Search query"),
    time_range: str = Query(default="-24h", description="Time range (e.g., -24h, -7d)"),
    provider: Optional[str] = Query(default=None, description="Specific SIEM provider"),
    current_user: User = Depends(get_current_user)
):
    """Search for events in SIEM systems."""
    
    try:
        if not settings.ENABLE_SIEM_INTEGRATION:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SIEM integration is disabled"
            )
        
        # Search events using SIEM orchestrator
        results = await siem_orchestrator.search_events(query, time_range, provider)
        
        logger.info(
            f"SIEM search performed by user {current_user.id}",
            query=query,
            time_range=time_range,
            provider=provider,
            results_count=len(results)
        )
        
        return results
        
    except Exception as e:
        logger.error(f"SIEM search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SIEM search failed: {str(e)}"
        )
