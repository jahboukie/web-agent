"""
Enterprise Tenant Management Service

Provides comprehensive tenant management for multi-tenant enterprise deployments
with security, compliance, and organizational features.
"""

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.security import EnterpriseTenant, user_tenant_roles
from app.models.user import User
from app.schemas.enterprise import EnterpriseTenantCreate, EnterpriseTenantUpdate

logger = get_logger(__name__)


class EnterpriseTenantService:
    """
    Enterprise Tenant Management Service

    Handles multi-tenant organization management with security,
    compliance, and organizational hierarchy features.
    """

    async def create_tenant(
        self, db: AsyncSession, tenant_data: EnterpriseTenantCreate, created_by: int
    ) -> EnterpriseTenant:
        """Create a new enterprise tenant."""

        try:
            # Check if tenant_id or domain already exists
            existing_check = await db.execute(
                select(EnterpriseTenant).where(
                    or_(
                        EnterpriseTenant.tenant_id == tenant_data.tenant_id,
                        EnterpriseTenant.domain == tenant_data.domain,
                    )
                )
            )
            if existing_check.scalar_one_or_none():
                raise ValueError("Tenant ID or domain already exists")

            # Create tenant
            db_tenant = EnterpriseTenant(
                tenant_id=tenant_data.tenant_id,
                name=tenant_data.name,
                display_name=tenant_data.display_name,
                domain=tenant_data.domain,
                is_active=tenant_data.is_active,
                is_enterprise=tenant_data.is_enterprise,
                compliance_level=tenant_data.compliance_level.value,
                subscription_tier=tenant_data.subscription_tier,
                max_users=tenant_data.max_users,
                max_concurrent_sessions=tenant_data.max_concurrent_sessions,
                api_rate_limit=tenant_data.api_rate_limit,
                enforce_sso=tenant_data.enforce_sso,
                require_mfa=tenant_data.require_mfa,
                session_timeout_minutes=tenant_data.session_timeout_minutes,
                password_policy=tenant_data.password_policy,
                data_region=tenant_data.data_region,
                encryption_required=tenant_data.encryption_required,
                audit_retention_days=tenant_data.audit_retention_days,
                admin_email=tenant_data.admin_email,
                billing_email=tenant_data.billing_email,
                support_contact=tenant_data.support_contact,
            )

            db.add(db_tenant)
            await db.commit()
            await db.refresh(db_tenant)

            logger.info(f"Created enterprise tenant: {tenant_data.tenant_id}")
            return db_tenant

        except Exception as e:
            logger.error(f"Failed to create tenant: {str(e)}")
            await db.rollback()
            raise

    async def get_tenant(
        self,
        db: AsyncSession,
        tenant_id: int | None = None,
        tenant_external_id: str | None = None,
        domain: str | None = None,
    ) -> EnterpriseTenant | None:
        """Get tenant by ID, external ID, or domain."""

        try:
            query = select(EnterpriseTenant)

            if tenant_id:
                query = query.where(EnterpriseTenant.id == tenant_id)
            elif tenant_external_id:
                query = query.where(EnterpriseTenant.tenant_id == tenant_external_id)
            elif domain:
                query = query.where(EnterpriseTenant.domain == domain)
            else:
                raise ValueError(
                    "Must provide tenant_id, tenant_external_id, or domain"
                )

            result = await db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get tenant: {str(e)}")
            return None

    async def update_tenant(
        self, db: AsyncSession, tenant_id: int, tenant_data: EnterpriseTenantUpdate
    ) -> EnterpriseTenant | None:
        """Update enterprise tenant."""

        try:
            # Get existing tenant
            result = await db.execute(
                select(EnterpriseTenant).where(EnterpriseTenant.id == tenant_id)
            )
            db_tenant = result.scalar_one_or_none()
            if not db_tenant:
                return None

            # Update fields
            update_data = tenant_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(db_tenant, field):
                    if field == "compliance_level" and value:
                        setattr(db_tenant, field, value.value)
                    else:
                        setattr(db_tenant, field, value)

            await db.commit()
            await db.refresh(db_tenant)

            logger.info(f"Updated tenant: {db_tenant.tenant_id}")
            return db_tenant

        except Exception as e:
            logger.error(f"Failed to update tenant: {str(e)}")
            await db.rollback()
            raise

    async def list_tenants(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        compliance_level: str | None = None,
    ) -> list[EnterpriseTenant]:
        """List enterprise tenants with filtering."""

        try:
            query = select(EnterpriseTenant)

            if is_active is not None:
                query = query.where(EnterpriseTenant.is_active == is_active)

            if compliance_level:
                query = query.where(
                    EnterpriseTenant.compliance_level == compliance_level
                )

            query = (
                query.offset(skip)
                .limit(limit)
                .order_by(EnterpriseTenant.created_at.desc())
            )

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to list tenants: {str(e)}")
            return []

    async def get_tenant_users(
        self,
        db: AsyncSession,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
        include_roles: bool = False,
    ) -> list[User]:
        """Get users belonging to a tenant."""

        try:
            query = (
                select(User)
                .join(user_tenant_roles, User.id == user_tenant_roles.c.user_id)
                .where(user_tenant_roles.c.tenant_id == tenant_id)
                .distinct()
            )

            if include_roles:
                query = query.options(selectinload(User.tenants))

            query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get tenant users: {str(e)}")
            return []

    async def get_tenant_stats(
        self, db: AsyncSession, tenant_id: int
    ) -> dict[str, Any]:
        """Get tenant statistics and metrics."""

        try:
            # Get user count
            user_count_result = await db.execute(
                select(func.count(func.distinct(user_tenant_roles.c.user_id))).where(
                    user_tenant_roles.c.tenant_id == tenant_id
                )
            )
            user_count = user_count_result.scalar() or 0

            # Get active user count (users with recent activity)
            # This would need to be implemented based on your activity tracking
            active_user_count = user_count  # Placeholder

            # Get tenant details
            tenant = await self.get_tenant(db, tenant_id=tenant_id)
            if not tenant:
                return {}

            return {
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
                "total_users": user_count,
                "active_users": active_user_count,
                "max_users": tenant.max_users,
                "user_utilization": (
                    (user_count / tenant.max_users * 100) if tenant.max_users > 0 else 0
                ),
                "compliance_level": tenant.compliance_level,
                "subscription_tier": tenant.subscription_tier,
                "is_active": tenant.is_active,
                "enforce_sso": tenant.enforce_sso,
                "require_mfa": tenant.require_mfa,
                "created_at": tenant.created_at,
                "data_region": tenant.data_region,
            }

        except Exception as e:
            logger.error(f"Failed to get tenant stats: {str(e)}")
            return {}

    async def check_tenant_limits(
        self, db: AsyncSession, tenant_id: int, check_type: str = "users"
    ) -> dict[str, Any]:
        """Check if tenant is within configured limits."""

        try:
            tenant = await self.get_tenant(db, tenant_id=tenant_id)
            if not tenant:
                return {"error": "Tenant not found"}

            if check_type == "users":
                # Check user limit
                user_count_result = await db.execute(
                    select(
                        func.count(func.distinct(user_tenant_roles.c.user_id))
                    ).where(user_tenant_roles.c.tenant_id == tenant_id)
                )
                current_users = user_count_result.scalar() or 0

                return {
                    "limit_type": "users",
                    "current": current_users,
                    "maximum": tenant.max_users,
                    "available": max(0, tenant.max_users - current_users),
                    "utilization_percent": (
                        (current_users / tenant.max_users * 100)
                        if tenant.max_users > 0
                        else 0
                    ),
                    "at_limit": current_users >= tenant.max_users,
                    "near_limit": (
                        current_users >= (tenant.max_users * 0.9)
                        if tenant.max_users > 0
                        else False
                    ),
                }

            return {"error": f"Unknown check type: {check_type}"}

        except Exception as e:
            logger.error(f"Failed to check tenant limits: {str(e)}")
            return {"error": str(e)}

    async def deactivate_tenant(
        self, db: AsyncSession, tenant_id: int, deactivated_by: int
    ) -> bool:
        """Deactivate a tenant (soft delete)."""

        try:
            result = await db.execute(
                select(EnterpriseTenant).where(EnterpriseTenant.id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                return False

            tenant.is_active = False
            await db.commit()

            logger.info(
                f"Deactivated tenant: {tenant.tenant_id} by user {deactivated_by}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to deactivate tenant: {str(e)}")
            await db.rollback()
            return False

    async def validate_tenant_domain(
        self, db: AsyncSession, domain: str, exclude_tenant_id: int | None = None
    ) -> bool:
        """Validate that tenant domain is unique."""

        try:
            query = select(EnterpriseTenant).where(EnterpriseTenant.domain == domain)

            if exclude_tenant_id:
                query = query.where(EnterpriseTenant.id != exclude_tenant_id)

            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            return existing is None

        except Exception as e:
            logger.error(f"Failed to validate tenant domain: {str(e)}")
            return False


# Global instance
enterprise_tenant_service = EnterpriseTenantService()
