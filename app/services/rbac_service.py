"""
Enterprise RBAC Service

Database-backed Role-Based Access Control service that integrates
Claude Code's RBAC engine with the new enterprise database models.
"""

import asyncio
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.security import (
    EnterpriseTenant, EnterpriseRole, EnterprisePermission, 
    AccessSession, user_tenant_roles
)
from app.models.user import User
from app.schemas.enterprise import (
    EnterpriseRoleCreate, EnterpriseRoleUpdate,
    EnterprisePermissionCreate
)
from app.schemas.user import UserTenantRoleAssignment
from app.security.rbac_engine import Permission, RBACEngine, enterprise_access_control
from app.security.zero_trust import zero_trust_engine
from app.core.config import settings

logger = get_logger(__name__)


class EnterpriseRBACService:
    """
    Enterprise RBAC Service
    
    Provides database-backed role and permission management with
    integration to Claude Code's existing RBAC engine.
    """
    
    def __init__(self):
        self.rbac_engine = enterprise_access_control.rbac_engine
        self._permission_cache = {}
        self._role_cache = {}
    
    async def initialize_system_permissions(self, db: AsyncSession) -> None:
        """Initialize system permissions in database from RBAC engine."""
        
        try:
            logger.info("Initializing system permissions")
            
            # Get existing permissions
            result = await db.execute(select(EnterprisePermission))
            existing_permissions = {p.permission_id: p for p in result.scalars().all()}
            
            # Define permission categories and mappings
            permission_mappings = {
                # User Management
                Permission.USERS_CREATE: ("users", "user", "create", False),
                Permission.USERS_READ: ("users", "user", "read", False),
                Permission.USERS_UPDATE: ("users", "user", "update", False),
                Permission.USERS_DELETE: ("users", "user", "delete", True),
                Permission.USERS_MANAGE_ROLES: ("users", "user", "manage_roles", True),
                
                # Task Management
                Permission.TASKS_CREATE: ("tasks", "task", "create", False),
                Permission.TASKS_READ_OWN: ("tasks", "task", "read_own", False),
                Permission.TASKS_READ_ALL: ("tasks", "task", "read_all", False),
                Permission.TASKS_UPDATE_OWN: ("tasks", "task", "update_own", False),
                Permission.TASKS_UPDATE_ALL: ("tasks", "task", "update_all", False),
                Permission.TASKS_DELETE_OWN: ("tasks", "task", "delete_own", False),
                Permission.TASKS_DELETE_ALL: ("tasks", "task", "delete_all", True),
                Permission.TASKS_EXECUTE: ("tasks", "task", "execute", False),
                Permission.TASKS_APPROVE: ("tasks", "task", "approve", True),
                
                # Execution Plan Management
                Permission.PLANS_CREATE: ("plans", "execution_plan", "create", False),
                Permission.PLANS_READ_OWN: ("plans", "execution_plan", "read_own", False),
                Permission.PLANS_READ_ALL: ("plans", "execution_plan", "read_all", False),
                Permission.PLANS_UPDATE_OWN: ("plans", "execution_plan", "update_own", False),
                Permission.PLANS_UPDATE_ALL: ("plans", "execution_plan", "update_all", False),
                Permission.PLANS_DELETE_OWN: ("plans", "execution_plan", "delete_own", False),
                Permission.PLANS_DELETE_ALL: ("plans", "execution_plan", "delete_all", True),
                Permission.PLANS_APPROVE: ("plans", "execution_plan", "approve", True),
                Permission.PLANS_VALIDATE: ("plans", "execution_plan", "validate", False),
                
                # Credential Management
                Permission.CREDENTIALS_CREATE: ("credentials", "credential", "create", False),
                Permission.CREDENTIALS_READ_OWN: ("credentials", "credential", "read_own", False),
                Permission.CREDENTIALS_READ_ALL: ("credentials", "credential", "read_all", True),
                Permission.CREDENTIALS_UPDATE_OWN: ("credentials", "credential", "update_own", False),
                Permission.CREDENTIALS_UPDATE_ALL: ("credentials", "credential", "update_all", True),
                Permission.CREDENTIALS_DELETE_OWN: ("credentials", "credential", "delete_own", False),
                Permission.CREDENTIALS_DELETE_ALL: ("credentials", "credential", "delete_all", True),
                
                # Security and Compliance
                Permission.SECURITY_POLICIES_READ: ("security", "security_policy", "read", False),
                Permission.SECURITY_POLICIES_WRITE: ("security", "security_policy", "write", True),
                Permission.COMPLIANCE_READ: ("compliance", "compliance_report", "read", False),
                Permission.COMPLIANCE_REPORTS_GENERATE: ("compliance", "compliance_report", "generate", True),
                Permission.AUDIT_LOGS_READ: ("audit", "audit_log", "read", True),
                
                # System Administration
                Permission.ADMIN_SYSTEM_CONFIG: ("system", "system", "configure", True),
                Permission.ADMIN_TENANT_MANAGE: ("tenant", "tenant", "manage", True),
                Permission.ADMIN_COMPLIANCE_MANAGE: ("compliance", "compliance", "manage", True),
                Permission.ADMIN_SECURITY_CONFIG: ("security", "security", "configure", True),
                Permission.ADMIN_BACKUP_RESTORE: ("system", "system", "backup_restore", True),
                
                # API Access
                Permission.API_AUTOMATION: ("api", "api", "automation", False),
                Permission.API_REPORTING: ("api", "api", "reporting", False),
                Permission.API_ADMIN: ("api", "api", "admin", True),
                
                # Wildcards
                Permission.ALL_PERMISSIONS: ("system", "all", "all", True),
                Permission.TENANT_ADMIN: ("tenant", "tenant", "admin", True),
                Permission.USER_OWN_RESOURCES: ("user", "resource", "own", False),
            }
            
            # Create missing permissions
            new_permissions = []
            for permission, (category, resource_type, action, is_dangerous) in permission_mappings.items():
                if permission.value not in existing_permissions:
                    perm = EnterprisePermission(
                        permission_id=permission.value,
                        name=permission.value.replace(":", "_").replace("_", " ").title(),
                        display_name=permission.value.replace(":", " - ").replace("_", " ").title(),
                        description=f"Permission to {action} {resource_type} resources",
                        category=category,
                        resource_type=resource_type,
                        action=action,
                        is_system_permission=True,
                        is_dangerous=is_dangerous,
                        risk_level="high" if is_dangerous else "low"
                    )
                    new_permissions.append(perm)
            
            if new_permissions:
                db.add_all(new_permissions)
                await db.commit()
                logger.info(f"Created {len(new_permissions)} system permissions")
            
        except Exception as e:
            logger.error(f"Failed to initialize system permissions: {str(e)}")
            await db.rollback()
            raise
    
    async def initialize_system_roles(self, db: AsyncSession) -> None:
        """Initialize system roles in database from RBAC engine."""
        
        try:
            logger.info("Initializing system roles")
            
            # Get existing roles and permissions
            roles_result = await db.execute(select(EnterpriseRole))
            existing_roles = {r.role_id: r for r in roles_result.scalars().all()}
            
            permissions_result = await db.execute(select(EnterprisePermission))
            permissions_map = {p.permission_id: p for p in permissions_result.scalars().all()}
            
            # Create system roles from RBAC engine
            for role_id, role_data in self.rbac_engine.roles.items():
                if role_id not in existing_roles:
                    # Create role
                    db_role = EnterpriseRole(
                        role_id=role_id,
                        name=role_data.name,
                        display_name=role_data.name,
                        description=role_data.description,
                        is_system_role=role_data.is_system_role,
                        is_tenant_scoped=role_data.tenant_scoped,
                        max_session_duration_hours=role_data.max_session_duration,
                        requires_approval=role_data.requires_approval,
                        risk_level=role_data.risk_level.value,
                        role_level=0 if role_id == "system_admin" else 1
                    )
                    db.add(db_role)
                    await db.flush()  # Get the ID
                    
                    # Add permissions to role
                    role_permissions = []
                    for permission in role_data.permissions:
                        if permission.value in permissions_map:
                            role_permissions.append(permissions_map[permission.value])
                    
                    db_role.permissions = role_permissions
                    
                    logger.info(f"Created system role: {role_id} with {len(role_permissions)} permissions")
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to initialize system roles: {str(e)}")
            await db.rollback()
            raise
    
    async def create_role(
        self, 
        db: AsyncSession, 
        role_data: EnterpriseRoleCreate,
        created_by: int
    ) -> EnterpriseRole:
        """Create a new enterprise role."""
        
        try:
            # Check if role already exists
            result = await db.execute(
                select(EnterpriseRole).where(EnterpriseRole.role_id == role_data.role_id)
            )
            if result.scalar_one_or_none():
                raise ValueError(f"Role with ID '{role_data.role_id}' already exists")
            
            # Create role
            db_role = EnterpriseRole(
                role_id=role_data.role_id,
                name=role_data.name,
                display_name=role_data.display_name,
                description=role_data.description,
                parent_role_id=role_data.parent_role_id,
                role_level=role_data.role_level,
                is_system_role=role_data.is_system_role,
                is_tenant_scoped=role_data.is_tenant_scoped,
                is_active=role_data.is_active,
                max_session_duration_hours=role_data.max_session_duration_hours,
                requires_approval=role_data.requires_approval,
                risk_level=role_data.risk_level.value,
                created_by=created_by
            )
            db.add(db_role)
            await db.flush()
            
            # Add permissions if specified
            if role_data.permission_ids:
                permissions_result = await db.execute(
                    select(EnterprisePermission).where(
                        EnterprisePermission.id.in_(role_data.permission_ids)
                    )
                )
                permissions = permissions_result.scalars().all()
                db_role.permissions = list(permissions)
            
            await db.commit()
            await db.refresh(db_role)
            
            logger.info(f"Created enterprise role: {role_data.role_id}")
            return db_role
            
        except Exception as e:
            logger.error(f"Failed to create role: {str(e)}")
            await db.rollback()
            raise
    
    async def assign_user_roles(
        self,
        db: AsyncSession,
        assignment: UserTenantRoleAssignment,
        assigned_by: int
    ) -> bool:
        """Assign roles to user in tenant."""
        
        try:
            # Verify user exists
            user_result = await db.execute(select(User).where(User.id == assignment.user_id))
            if not user_result.scalar_one_or_none():
                raise ValueError(f"User {assignment.user_id} not found")
            
            # Verify tenant exists
            tenant_result = await db.execute(
                select(EnterpriseTenant).where(EnterpriseTenant.id == assignment.tenant_id)
            )
            if not tenant_result.scalar_one_or_none():
                raise ValueError(f"Tenant {assignment.tenant_id} not found")
            
            # Verify roles exist
            roles_result = await db.execute(
                select(EnterpriseRole).where(EnterpriseRole.id.in_(assignment.role_ids))
            )
            roles = roles_result.scalars().all()
            if len(roles) != len(assignment.role_ids):
                raise ValueError("One or more roles not found")
            
            # Remove existing assignments for this user-tenant combination
            await db.execute(
                user_tenant_roles.delete().where(
                    and_(
                        user_tenant_roles.c.user_id == assignment.user_id,
                        user_tenant_roles.c.tenant_id == assignment.tenant_id
                    )
                )
            )
            
            # Create new assignments
            for role_id in assignment.role_ids:
                await db.execute(
                    user_tenant_roles.insert().values(
                        user_id=assignment.user_id,
                        tenant_id=assignment.tenant_id,
                        role_id=role_id,
                        assigned_by=assigned_by,
                        expires_at=assignment.expires_at
                    )
                )
            
            await db.commit()
            
            logger.info(
                f"Assigned {len(assignment.role_ids)} roles to user {assignment.user_id} "
                f"in tenant {assignment.tenant_id}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign user roles: {str(e)}")
            await db.rollback()
            raise
    
    async def check_user_permission(
        self,
        db: AsyncSession,
        user_id: int,
        permission: str,
        tenant_id: Optional[int] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission in tenant context."""
        
        try:
            # Get user's roles in tenant
            query = select(EnterpriseRole).join(
                user_tenant_roles,
                EnterpriseRole.id == user_tenant_roles.c.role_id
            ).where(
                user_tenant_roles.c.user_id == user_id
            )
            
            if tenant_id:
                query = query.where(user_tenant_roles.c.tenant_id == tenant_id)
            
            # Include permissions in query
            query = query.options(selectinload(EnterpriseRole.permissions))
            
            result = await db.execute(query)
            user_roles = result.scalars().all()
            
            # Check permissions
            for role in user_roles:
                for perm in role.permissions:
                    if perm.permission_id == permission:
                        return True
                    
                    # Check wildcard permissions
                    if perm.permission_id == "*":  # ALL_PERMISSIONS
                        return True
                    
                    if tenant_id and perm.permission_id == "tenant:*":  # TENANT_ADMIN
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check user permission: {str(e)}")
            return False
    
    async def get_user_permissions(
        self,
        db: AsyncSession,
        user_id: int,
        tenant_id: Optional[int] = None
    ) -> Set[str]:
        """Get all permissions for user in tenant context."""
        
        try:
            # Get user's roles in tenant
            query = select(EnterpriseRole).join(
                user_tenant_roles,
                EnterpriseRole.id == user_tenant_roles.c.role_id
            ).where(
                user_tenant_roles.c.user_id == user_id
            )
            
            if tenant_id:
                query = query.where(user_tenant_roles.c.tenant_id == tenant_id)
            
            query = query.options(selectinload(EnterpriseRole.permissions))
            
            result = await db.execute(query)
            user_roles = result.scalars().all()
            
            # Collect all permissions
            permissions = set()
            for role in user_roles:
                for perm in role.permissions:
                    permissions.add(perm.permission_id)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {str(e)}")
            return set()


    async def create_access_session(
        self,
        db: AsyncSession,
        user_id: int,
        tenant_id: Optional[int] = None,
        session_data: Dict[str, Any] = None
    ) -> AccessSession:
        """Create a new access session with Zero Trust verification."""

        try:
            from app.models.security import AccessSession
            import secrets

            session_id = f"sess_{secrets.token_hex(16)}"
            expires_at = datetime.utcnow() + timedelta(hours=8)  # Default 8 hours

            # Calculate initial trust score based on context
            initial_trust_score = await self._calculate_initial_trust_score(
                user_id, session_data or {}
            )

            # Create access session
            access_session = AccessSession(
                session_id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                is_active=True,
                is_sso_session=session_data.get("is_sso", False) if session_data else False,
                sso_session_id=session_data.get("sso_session_id") if session_data else None,
                device_fingerprint=session_data.get("device_fingerprint") if session_data else None,
                ip_address=session_data.get("ip_address") if session_data else None,
                user_agent=session_data.get("user_agent") if session_data else None,
                geolocation=session_data.get("geolocation", {}) if session_data else {},
                initial_trust_score=initial_trust_score,
                current_trust_score=initial_trust_score,
                risk_factors=session_data.get("risk_factors", []) if session_data else [],
                expires_at=expires_at,
                requires_mfa=session_data.get("requires_mfa", False) if session_data else False,
                requires_device_trust=session_data.get("requires_device_trust", False) if session_data else False
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
        self,
        user_id: int,
        session_data: Dict[str, Any]
    ) -> float:
        """Calculate initial trust score for new session using Zero Trust engine."""

        try:
            if settings.ENABLE_ZERO_TRUST:
                # Create AccessContext from session data
                from app.schemas.user import AccessContext, DeviceInfo

                device_info = None
                if session_data.get("device_fingerprint"):
                    device_info = DeviceInfo(
                        device_id=session_data.get("device_fingerprint"),
                        device_type=session_data.get("device_type", "unknown"),
                        user_agent=session_data.get("user_agent", ""),
                        encrypted=session_data.get("device_encrypted", False)
                    )

                access_context = AccessContext(
                    timestamp=datetime.utcnow(),
                    source_ip=session_data.get("ip_address"),
                    user_agent=session_data.get("user_agent"),
                    device_info=device_info,
                    geolocation=session_data.get("geolocation", {}),
                    network_type=session_data.get("network_type", "unknown"),
                    mfa_verified=session_data.get("mfa_verified", False),
                    risk_score=0.0  # Will be calculated by Zero Trust engine
                )

                # Get Zero Trust assessment
                trust_assessment = await zero_trust_engine.calculate_trust_score(
                    user_id, access_context
                )

                return trust_assessment.trust_score

            else:
                # Fallback to simple calculation
                return await self._fallback_trust_calculation(user_id, session_data)

        except Exception as e:
            logger.warning(f"Zero Trust calculation failed, using fallback: {str(e)}")
            return await self._fallback_trust_calculation(user_id, session_data)

    async def _fallback_trust_calculation(
        self,
        user_id: int,
        session_data: Dict[str, Any]
    ) -> float:
        """Fallback trust score calculation when Zero Trust is unavailable."""

        base_score = 1.0

        # Reduce score for unknown devices
        if not session_data.get("device_fingerprint"):
            base_score -= 0.2

        # Reduce score for suspicious IP addresses
        ip_address = session_data.get("ip_address")
        if ip_address and self._is_suspicious_ip(ip_address):
            base_score -= 0.3

        # Reduce score for unusual geolocation
        geolocation = session_data.get("geolocation", {})
        if geolocation and self._is_unusual_location(user_id, geolocation):
            base_score -= 0.2

        # Increase score for SSO authentication
        if session_data.get("is_sso"):
            base_score += 0.1

        return max(0.0, min(1.0, base_score))

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address is suspicious (placeholder implementation)."""
        # This would integrate with threat intelligence feeds
        return False

    def _is_unusual_location(self, user_id: int, geolocation: Dict[str, Any]) -> bool:
        """Check if location is unusual for user (placeholder implementation)."""
        # This would check against user's historical locations
        return False


# Global instance
enterprise_rbac_service = EnterpriseRBACService()
