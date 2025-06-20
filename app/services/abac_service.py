"""
Enterprise ABAC (Attribute-Based Access Control) Service

Database-backed ABAC policy engine that provides fine-grained access control
based on user, resource, environment, and action attributes with dynamic
policy evaluation and Zero Trust integration.
"""

import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.security import ABACPolicy, AccessSession
from app.models.user import User
from app.schemas.enterprise import ABACPolicyCreate, ABACPolicyUpdate
from app.security.rbac_engine import AccessRequest, AccessDecision, AccessContext
from app.security.zero_trust import zero_trust_engine
from app.core.config import settings

logger = get_logger(__name__)


class ABACPolicyEngine:
    """
    Enterprise ABAC Policy Engine
    
    Provides database-backed attribute-based access control with
    dynamic policy evaluation and Zero Trust integration.
    """
    
    def __init__(self):
        self.zero_trust_engine = zero_trust_engine
        self._policy_cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_update = {}
    
    async def create_policy(
        self,
        db: AsyncSession,
        policy_data: ABACPolicyCreate,
        created_by: int
    ) -> ABACPolicy:
        """Create a new ABAC policy."""
        
        try:
            # Validate policy conditions
            await self._validate_policy_conditions(policy_data.conditions)
            
            # Check if policy already exists
            result = await db.execute(
                select(ABACPolicy).where(ABACPolicy.policy_id == policy_data.policy_id)
            )
            if result.scalar_one_or_none():
                raise ValueError(f"Policy with ID '{policy_data.policy_id}' already exists")
            
            # Create policy
            db_policy = ABACPolicy(
                policy_id=policy_data.policy_id,
                tenant_id=policy_data.tenant_id,
                name=policy_data.name,
                description=policy_data.description,
                effect=policy_data.effect,
                priority=policy_data.priority,
                conditions=policy_data.conditions,
                resources=policy_data.resources,
                actions=policy_data.actions,
                is_active=policy_data.is_active,
                is_system_policy=policy_data.is_system_policy,
                version=policy_data.version,
                created_by=created_by
            )
            
            db.add(db_policy)
            await db.commit()
            await db.refresh(db_policy)
            
            # Clear cache
            self._clear_policy_cache()
            
            logger.info(f"Created ABAC policy: {policy_data.policy_id}")
            return db_policy
            
        except Exception as e:
            logger.error(f"Failed to create ABAC policy: {str(e)}")
            await db.rollback()
            raise
    
    async def evaluate_access(
        self,
        db: AsyncSession,
        user_id: int,
        resource_type: str,
        resource_id: str,
        action: str,
        tenant_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AccessDecision:
        """Evaluate access request against ABAC policies."""
        
        try:
            request_id = f"abac_{datetime.utcnow().timestamp()}"
            
            # Get applicable policies
            policies = await self._get_applicable_policies(
                db, resource_type, action, tenant_id
            )
            
            if not policies:
                return AccessDecision(
                    request_id=request_id,
                    decision="ABSTAIN",
                    reason="No applicable ABAC policies found"
                )
            
            # Get user attributes
            user_attributes = await self._get_user_attributes(db, user_id)
            
            # Get resource attributes
            resource_attributes = await self._get_resource_attributes(
                db, resource_type, resource_id
            )
            
            # Get environment attributes
            environment_attributes = await self._get_environment_attributes(
                db, user_id, context or {}
            )
            
            # Combine all attributes
            all_attributes = {
                **user_attributes,
                **resource_attributes,
                **environment_attributes,
                "action.type": action,
                "resource.type": resource_type,
                "resource.id": resource_id
            }
            
            # Evaluate policies in priority order
            policies.sort(key=lambda p: p.priority, reverse=True)
            
            applicable_policies = []
            final_decision = "ABSTAIN"
            decision_reason = "No policies matched"
            
            for policy in policies:
                if await self._evaluate_policy_conditions(policy, all_attributes):
                    applicable_policies.append(policy.policy_id)
                    final_decision = policy.effect
                    decision_reason = f"Policy '{policy.name}' evaluated to {policy.effect}"
                    
                    # Update policy evaluation count
                    policy.evaluation_count += 1
                    policy.last_evaluated_at = datetime.utcnow()
                    
                    # DENY takes precedence over ALLOW
                    if policy.effect == "DENY":
                        break
            
            # Commit policy updates
            await db.commit()
            
            return AccessDecision(
                request_id=request_id,
                decision=final_decision,
                reason=decision_reason,
                applicable_policies=applicable_policies,
                evaluated_attributes=all_attributes
            )
            
        except Exception as e:
            logger.error(f"ABAC access evaluation failed: {str(e)}")
            return AccessDecision(
                request_id=f"abac_error_{datetime.utcnow().timestamp()}",
                decision="DENY",
                reason=f"ABAC evaluation error: {str(e)}"
            )
    
    async def _get_applicable_policies(
        self,
        db: AsyncSession,
        resource_type: str,
        action: str,
        tenant_id: Optional[int] = None
    ) -> List[ABACPolicy]:
        """Get policies applicable to the resource type and action."""
        
        try:
            query = select(ABACPolicy).where(
                and_(
                    ABACPolicy.is_active == True,
                    or_(
                        ABACPolicy.tenant_id == tenant_id,
                        ABACPolicy.tenant_id.is_(None),  # System policies
                        ABACPolicy.is_system_policy == True
                    )
                )
            )
            
            result = await db.execute(query)
            all_policies = result.scalars().all()
            
            # Filter policies by resource and action patterns
            applicable_policies = []
            for policy in all_policies:
                if self._matches_resource_pattern(policy.resources, resource_type):
                    if self._matches_action_pattern(policy.actions, action):
                        applicable_policies.append(policy)
            
            return applicable_policies
            
        except Exception as e:
            logger.error(f"Failed to get applicable policies: {str(e)}")
            return []
    
    def _matches_resource_pattern(self, resource_patterns: List[str], resource_type: str) -> bool:
        """Check if resource type matches any pattern."""
        if not resource_patterns:
            return True  # Empty list matches all
        
        for pattern in resource_patterns:
            if pattern == "*" or pattern == resource_type:
                return True
            if pattern.endswith("*") and resource_type.startswith(pattern[:-1]):
                return True
        
        return False
    
    def _matches_action_pattern(self, action_patterns: List[str], action: str) -> bool:
        """Check if action matches any pattern."""
        if not action_patterns:
            return True  # Empty list matches all
        
        for pattern in action_patterns:
            if pattern == "*" or pattern == action:
                return True
            if pattern.endswith("*") and action.startswith(pattern[:-1]):
                return True
        
        return False
    
    async def _get_user_attributes(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Get user attributes for policy evaluation."""
        
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                return {}
            
            return {
                "user.id": user.id,
                "user.email": user.email,
                "user.username": user.username,
                "user.is_active": user.is_active,
                "user.is_superuser": user.is_superuser,
                "user.employee_id": user.employee_id,
                "user.department": user.department,
                "user.job_title": user.job_title,
                "user.mfa_enabled": user.mfa_enabled,
                "user.data_classification": user.data_classification,
                "user.gdpr_consent": user.gdpr_consent,
                "user.sso_provider": user.sso_provider,
                "user.trust_score": user.trust_score.get("current", 1.0) if user.trust_score else 1.0,
                "user.risk_profile": user.risk_profile.get("level", "low") if user.risk_profile else "low"
            }
            
        except Exception as e:
            logger.error(f"Failed to get user attributes: {str(e)}")
            return {}
    
    async def _get_resource_attributes(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: str
    ) -> Dict[str, Any]:
        """Get resource attributes for policy evaluation."""
        
        # This would be implemented based on your specific resource types
        # For now, return basic attributes
        return {
            "resource.type": resource_type,
            "resource.id": resource_id,
            "resource.classification": "internal",  # Default classification
            "resource.sensitivity": "normal"
        }
    
    async def _get_environment_attributes(
        self,
        db: AsyncSession,
        user_id: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get environment attributes for policy evaluation."""
        
        try:
            # Get current access session if available
            session_attributes = {}
            if context.get("session_id"):
                session_result = await db.execute(
                    select(AccessSession).where(
                        AccessSession.session_id == context["session_id"]
                    )
                )
                session = session_result.scalar_one_or_none()
                if session:
                    session_attributes = {
                        "env.device_fingerprint": session.device_fingerprint,
                        "env.ip_address": session.ip_address,
                        "env.user_agent": session.user_agent,
                        "env.geolocation": session.geolocation,
                        "env.trust_score": session.current_trust_score,
                        "env.is_sso_session": session.is_sso_session,
                        "env.mfa_verified": session.mfa_verified_at is not None,
                        "env.device_trusted": session.device_trusted_at is not None
                    }
            
            # Add time-based attributes
            now = datetime.utcnow()
            time_attributes = {
                "env.time_of_day": now.hour,
                "env.day_of_week": now.weekday(),
                "env.is_business_hours": 9 <= now.hour <= 17 and now.weekday() < 5,
                "env.timestamp": now.timestamp()
            }
            
            # Add context attributes
            context_attributes = {
                f"env.{key}": value for key, value in context.items()
                if key not in ["session_id"]
            }

            # Add Zero Trust attributes if available
            zero_trust_attributes = {}
            if settings.ENABLE_ZERO_TRUST and context.get("access_context"):
                try:
                    access_context = context["access_context"]
                    trust_assessment = await self.zero_trust_engine.calculate_trust_score(
                        user_id, access_context
                    )
                    zero_trust_attributes = {
                        "env.trust_score": trust_assessment.trust_score,
                        "env.trust_level": trust_assessment.trust_level.value,
                        "env.risk_score": trust_assessment.risk_score,
                        "env.confidence_score": trust_assessment.confidence_score,
                        "env.risk_factors_count": len(trust_assessment.risk_factors)
                    }
                except Exception as e:
                    logger.warning(f"Zero Trust assessment failed: {str(e)}")

            return {
                **session_attributes,
                **time_attributes,
                **context_attributes,
                **zero_trust_attributes
            }
            
        except Exception as e:
            logger.error(f"Failed to get environment attributes: {str(e)}")
            return {}
    
    async def _evaluate_policy_conditions(
        self,
        policy: ABACPolicy,
        attributes: Dict[str, Any]
    ) -> bool:
        """Evaluate policy conditions against attributes."""
        
        try:
            conditions = policy.conditions
            if not conditions:
                return True  # No conditions means always match
            
            for attr_name, condition in conditions.items():
                attr_value = attributes.get(attr_name)
                
                if not self._evaluate_condition(attr_value, condition):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to evaluate policy conditions: {str(e)}")
            return False
    
    def _evaluate_condition(self, attr_value: Any, condition: Dict[str, Any]) -> bool:
        """Evaluate a single condition."""
        
        try:
            if "eq" in condition:
                return attr_value == condition["eq"]
            
            if "ne" in condition:
                return attr_value != condition["ne"]
            
            if "in" in condition:
                return attr_value in condition["in"]
            
            if "not_in" in condition:
                return attr_value not in condition["not_in"]
            
            if "gt" in condition:
                return attr_value > condition["gt"]
            
            if "gte" in condition:
                return attr_value >= condition["gte"]
            
            if "lt" in condition:
                return attr_value < condition["lt"]
            
            if "lte" in condition:
                return attr_value <= condition["lte"]
            
            if "contains" in condition:
                return condition["contains"] in str(attr_value)
            
            if "starts_with" in condition:
                return str(attr_value).startswith(condition["starts_with"])
            
            if "ends_with" in condition:
                return str(attr_value).endswith(condition["ends_with"])
            
            if "regex" in condition:
                import re
                return bool(re.match(condition["regex"], str(attr_value)))
            
            return True  # Unknown condition type defaults to true
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {str(e)}")
            return False
    
    async def _validate_policy_conditions(self, conditions: Dict[str, Any]) -> None:
        """Validate policy conditions syntax."""
        
        valid_operators = {
            "eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte",
            "contains", "starts_with", "ends_with", "regex"
        }
        
        for attr_name, condition in conditions.items():
            if not isinstance(condition, dict):
                raise ValueError(f"Condition for '{attr_name}' must be a dictionary")
            
            for operator in condition.keys():
                if operator not in valid_operators:
                    raise ValueError(f"Invalid operator '{operator}' in condition for '{attr_name}'")
    
    def _clear_policy_cache(self):
        """Clear the policy cache."""
        self._policy_cache.clear()
        self._last_cache_update.clear()


# Global instance
enterprise_abac_service = ABACPolicyEngine()
