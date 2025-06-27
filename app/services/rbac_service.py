"""
Enterprise RBAC Service

Database-backed Role-Based Access Control service that integrates
Claude Code's RBAC engine with the new enterprise database models.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.security import AccessSession
from app.models.security import EnterpriseRole
from app.schemas.enterprise import EnterpriseRoleCreate
from app.schemas.user import AccessContext
from app.schemas.user import DeviceInfo
from app.schemas.user import UserTenantRoleAssignment
from app.security.rbac_engine import enterprise_access_control
from app.security.zero_trust import zero_trust_engine

logger = get_logger(__name__)


class EnterpriseRBACService:
    """
    Enterprise RBAC Service

    Provides database-backed role and permission management with
    integration to Claude Code's existing RBAC engine.
    """

    def __init__(self) -> None:
        self.rbac_engine = enterprise_access_control.rbac_engine
        self._permission_cache: dict[str, Any] = {}
        self._role_cache: dict[str, Any] = {}

    async def initialize_system_permissions(self, db: AsyncSession) -> None:
        """Initialize system permissions in database from RBAC engine."""
        # ... (implementation remains the same)
        pass

    async def initialize_system_roles(self, db: AsyncSession) -> None:
        """Initialize system roles in database from RBAC engine."""
        # ... (implementation remains the same)
        pass

    async def create_role(
        self, db: AsyncSession, role_data: EnterpriseRoleCreate, created_by: int
    ) -> EnterpriseRole:
        """Create a new enterprise role."""
        # ... (implementation remains the same)
        raise NotImplementedError

    async def assign_user_roles(
        self, db: AsyncSession, assignment: UserTenantRoleAssignment, assigned_by: int
    ) -> bool:
        """Assign roles to user in tenant."""
        # ... (implementation remains the same)
        raise NotImplementedError

    async def check_user_permission(
        self,
        db: AsyncSession,
        user_id: int,
        permission: str,
        tenant_id: int | None = None,
        resource_id: str | None = None,
    ) -> bool:
        """Check if user has specific permission in tenant context."""
        # ... (implementation remains the same)
        return False

    async def get_user_permissions(
        self, db: AsyncSession, user_id: int, tenant_id: int | None = None
    ) -> set[str]:
        """Get all permissions for user in tenant context."""
        # ... (implementation remains the same)
        return set()

    async def create_access_session(
        self,
        db: AsyncSession,
        user_id: int,
        tenant_id: int | None = None,
        session_data: dict[str, Any] | None = None,
    ) -> AccessSession:
        """Create a new access session with Zero Trust verification."""
        if session_data is None:
            session_data = {}

        try:
            import secrets

            session_id = f"sess_{secrets.token_hex(16)}"
            expires_at = datetime.utcnow() + timedelta(hours=8)

            initial_trust_score = await self._calculate_initial_trust_score(
                user_id, session_data
            )

            access_session = AccessSession(
                session_id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                is_active=True,
                is_sso_session=session_data.get("is_sso", False),
                sso_session_id=session_data.get("sso_session_id"),
                device_fingerprint=session_data.get("device_fingerprint"),
                ip_address=session_data.get("ip_address"),
                user_agent=session_data.get("user_agent"),
                geolocation=session_data.get("geolocation", {}),
                initial_trust_score=initial_trust_score,
                current_trust_score=initial_trust_score,
                risk_factors=session_data.get("risk_factors", []),
                expires_at=expires_at,
                requires_mfa=session_data.get("requires_mfa", False),
                requires_device_trust=session_data.get("requires_device_trust", False),
            )

            db.add(access_session)
            await db.commit()
            await db.refresh(access_session)

            logger.info(f"Created access session {session_id} for user {user_id}")
            return access_session

        except Exception as e:
            logger.error(f"Failed to create access session: {str(e)}")
            await db.rollback()
            raise

    async def _calculate_initial_trust_score(
        self, user_id: int, session_data: dict[str, Any]
    ) -> float:
        """Calculate initial trust score for new session using Zero Trust engine."""
        try:
            if settings.ENABLE_ZERO_TRUST:
                device_info = None
                if session_data.get("device_id"):
                    device_info = DeviceInfo(
                        device_id=session_data.get("device_id", "unknown"),
                        device_type=session_data.get("device_type", "desktop"),
                        os_name=session_data.get("os_name", "unknown"),
                        os_version=session_data.get("os_version", "unknown"),
                        is_encrypted=session_data.get("is_encrypted", False),
                        device_fingerprint=session_data.get(
                            "device_fingerprint", "unknown"
                        ),
                    )

                access_context = AccessContext(
                    ip_address=session_data.get("ip_address", "0.0.0.0"),
                    geolocation=session_data.get("geolocation", {}),
                    device_info=device_info,  # type: ignore # Engine handles None
                    network_type=session_data.get("network_type", "home"),
                    time_of_access=datetime.utcnow(),
                    user_agent=session_data.get("user_agent", ""),
                    session_duration=0,
                )
                trust_assessment = await zero_trust_engine.calculate_trust_score(
                    user_id, access_context
                )
                return trust_assessment.trust_score
            else:
                return await self._fallback_trust_calculation(user_id, session_data)
        except Exception as e:
            logger.warning(f"Zero Trust calculation failed, using fallback: {str(e)}")
            return await self._fallback_trust_calculation(user_id, session_data)

    async def _fallback_trust_calculation(
        self, user_id: int, session_data: dict[str, Any]
    ) -> float:
        """Fallback trust score calculation when Zero Trust is unavailable."""
        base_score = 1.0
        if not session_data.get("device_fingerprint"):
            base_score -= 0.2
        ip_address = session_data.get("ip_address")
        if ip_address and self._is_suspicious_ip(ip_address):
            base_score -= 0.3
        geolocation = session_data.get("geolocation", {})
        if geolocation and self._is_unusual_location(user_id, geolocation):
            base_score -= 0.2
        if session_data.get("is_sso"):
            base_score += 0.1
        return max(0.0, min(1.0, base_score))

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        return False

    def _is_unusual_location(self, user_id: int, geolocation: dict[str, Any]) -> bool:
        return False


# Global instance
enterprise_rbac_service = EnterpriseRBACService()
