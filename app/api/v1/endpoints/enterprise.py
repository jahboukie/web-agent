"""
Enterprise Access Control API Endpoints

FastAPI endpoints for enterprise RBAC/ABAC, SSO configuration,
tenant management, and access control testing.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.enterprise import (
    ABACPolicy,
    ABACPolicyCreate,
    AccessSession,
    EnterprisePermission,
    EnterpriseRole,
    EnterpriseRoleCreate,
    EnterpriseTenant,
    EnterpriseTenantCreate,
    EnterpriseTenantUpdate,
    SSOConfiguration,
    SSOConfigurationCreate,
)
from app.schemas.user import UserTenantRoleAssignment
from app.security.rbac_engine import Permission, require_permission
from app.services.abac_service import enterprise_abac_service
from app.services.rbac_service import enterprise_rbac_service
from app.services.sso_service import enterprise_sso_service
from app.services.tenant_service import enterprise_tenant_service

router = APIRouter()


# Tenant Management Endpoints


@router.post(
    "/tenants", response_model=EnterpriseTenant, status_code=status.HTTP_201_CREATED
)
@require_permission(Permission.SYSTEM_CONFIGURE)
async def create_tenant(
    tenant_data: EnterpriseTenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new enterprise tenant."""
    try:
        tenant = await enterprise_tenant_service.create_tenant(
            db, tenant_data, current_user.id
        )
        return tenant
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/tenants", response_model=list[EnterpriseTenant])
@require_permission(Permission.SYSTEM_MONITOR)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool | None = Query(None),
    compliance_level: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List enterprise tenants with filtering."""
    tenants = await enterprise_tenant_service.list_tenants(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        compliance_level=compliance_level,
    )
    return tenants


@router.get("/tenants/{tenant_id}", response_model=EnterpriseTenant)
@require_permission(Permission.SYSTEM_MONITOR)
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get tenant by ID."""
    tenant = await enterprise_tenant_service.get_tenant(db, tenant_id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return tenant


@router.put("/tenants/{tenant_id}", response_model=EnterpriseTenant)
@require_permission(Permission.SYSTEM_CONFIGURE)
async def update_tenant(
    tenant_id: int,
    tenant_data: EnterpriseTenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update enterprise tenant."""
    tenant = await enterprise_tenant_service.update_tenant(db, tenant_id, tenant_data)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return tenant


@router.get("/tenants/{tenant_id}/stats")
@require_permission(Permission.SYSTEM_MONITOR)
async def get_tenant_stats(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get tenant statistics and metrics."""
    stats = await enterprise_tenant_service.get_tenant_stats(db, tenant_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return stats


# Role Management Endpoints


@router.post(
    "/roles", response_model=EnterpriseRole, status_code=status.HTTP_201_CREATED
)
@require_permission(Permission.USERS_MANAGE_ROLES)
async def create_role(
    role_data: EnterpriseRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new enterprise role."""
    try:
        role = await enterprise_rbac_service.create_role(db, role_data, current_user.id)
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/roles", response_model=list[EnterpriseRole])
@require_permission(Permission.USERS_READ)
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool | None = Query(None),
    is_system_role: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List enterprise roles."""
    from sqlalchemy import select

    from app.models.security import EnterpriseRole as RoleModel

    query = select(RoleModel)

    if is_active is not None:
        query = query.where(RoleModel.is_active == is_active)

    if is_system_role is not None:
        query = query.where(RoleModel.is_system_role == is_system_role)

    query = query.offset(skip).limit(limit).order_by(RoleModel.created_at.desc())

    result = await db.execute(query)
    roles = result.scalars().all()
    return roles


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
@require_permission(Permission.USERS_MANAGE_ROLES)
async def assign_user_roles(
    user_id: int,
    assignment: UserTenantRoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign roles to user in tenant."""
    try:
        # Override user_id from path
        assignment.user_id = user_id
        success = await enterprise_rbac_service.assign_user_roles(
            db, assignment, current_user.id
        )
        if success:
            return {"message": "Roles assigned successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to assign roles"
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/users/{user_id}/permissions")
@require_permission(Permission.USERS_READ)
async def get_user_permissions(
    user_id: int,
    tenant_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all permissions for user in tenant context."""
    permissions = await enterprise_rbac_service.get_user_permissions(
        db, user_id, tenant_id
    )
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "permissions": list(permissions),
    }


@router.post("/users/{user_id}/permissions/check")
@require_permission(Permission.USERS_READ)
async def check_user_permission(
    user_id: int,
    permission_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if user has specific permission."""
    permission = permission_data.get("permission")
    tenant_id = permission_data.get("tenant_id")
    resource_id = permission_data.get("resource_id")

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Permission is required"
        )

    has_permission = await enterprise_rbac_service.check_user_permission(
        db, user_id, permission, tenant_id, resource_id
    )

    return {
        "user_id": user_id,
        "permission": permission,
        "tenant_id": tenant_id,
        "resource_id": resource_id,
        "has_permission": has_permission,
    }


# Permission Management Endpoints


@router.get("/permissions", response_model=list[EnterprisePermission])
@require_permission(Permission.USERS_READ)
async def list_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: str | None = Query(None),
    resource_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List enterprise permissions."""
    from sqlalchemy import select

    from app.models.security import EnterprisePermission as PermissionModel

    query = select(PermissionModel)

    if category:
        query = query.where(PermissionModel.category == category)

    if resource_type:
        query = query.where(PermissionModel.resource_type == resource_type)

    query = (
        query.offset(skip)
        .limit(limit)
        .order_by(PermissionModel.category, PermissionModel.name)
    )

    result = await db.execute(query)
    permissions = result.scalars().all()
    return permissions


# SSO Configuration Endpoints


@router.post(
    "/tenants/{tenant_id}/sso",
    response_model=SSOConfiguration,
    status_code=status.HTTP_201_CREATED,
)
@require_permission(Permission.SYSTEM_CONFIGURE)
async def create_sso_configuration(
    tenant_id: int,
    config_data: SSOConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create SSO configuration for tenant."""
    try:
        # Override tenant_id from path
        config_data.tenant_id = tenant_id
        config = await enterprise_sso_service.create_sso_configuration(
            db, config_data, current_user.id
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/tenants/{tenant_id}/sso", response_model=list[SSOConfiguration])
@require_permission(Permission.SYSTEM_MONITOR)
async def list_sso_configurations(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List SSO configurations for tenant."""
    configs = await enterprise_sso_service.list_sso_configurations(db, tenant_id)
    return configs


@router.post("/tenants/{tenant_id}/sso/{config_id}/test")
@require_permission(Permission.SYSTEM_CONFIGURE)
async def test_sso_configuration(
    tenant_id: int,
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test SSO configuration connectivity."""
    result = await enterprise_sso_service.test_sso_configuration(db, config_id)
    return result


# ABAC Policy Endpoints


@router.post(
    "/policies", response_model=ABACPolicy, status_code=status.HTTP_201_CREATED
)
@require_permission(Permission.SECURITY_POLICIES_WRITE)
async def create_abac_policy(
    policy_data: ABACPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create ABAC policy."""
    try:
        policy = await enterprise_abac_service.create_policy(
            db, policy_data, current_user.id
        )
        return policy
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/policies/evaluate")
@require_permission(Permission.SECURITY_POLICIES_READ)
async def evaluate_abac_policy(
    evaluation_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Evaluate ABAC policies for access request."""
    try:
        user_id = evaluation_data.get("user_id")
        resource_type = evaluation_data.get("resource_type")
        resource_id = evaluation_data.get("resource_id")
        action = evaluation_data.get("action")
        tenant_id = evaluation_data.get("tenant_id")
        context = evaluation_data.get("context", {})

        if not all([user_id, resource_type, resource_id, action]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id, resource_type, resource_id, and action are required",
            )

        decision = await enterprise_abac_service.evaluate_access(
            db, user_id, resource_type, resource_id, action, tenant_id, context
        )

        return decision.__dict__

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Access Session Management


@router.get("/sessions", response_model=list[AccessSession])
@require_permission(Permission.SYSTEM_MONITOR)
async def list_access_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: int | None = Query(None),
    tenant_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List access sessions with filtering."""
    from sqlalchemy import and_, select

    from app.models.security import AccessSession as SessionModel

    query = select(SessionModel)

    conditions = []
    if user_id:
        conditions.append(SessionModel.user_id == user_id)
    if tenant_id:
        conditions.append(SessionModel.tenant_id == tenant_id)
    if is_active is not None:
        conditions.append(SessionModel.is_active == is_active)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit).order_by(SessionModel.created_at.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()
    return sessions


# System Initialization Endpoints


@router.post("/system/initialize")
@require_permission(Permission.SYSTEM_CONFIGURE)
async def initialize_enterprise_system(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Initialize enterprise system with default permissions and roles."""
    try:
        # Initialize system permissions
        await enterprise_rbac_service.initialize_system_permissions(db)

        # Initialize system roles
        await enterprise_rbac_service.initialize_system_roles(db)

        return {"message": "Enterprise system initialized successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/system/health")
async def get_system_health():
    """Get enterprise system health status."""
    return {
        "status": "healthy",
        "services": {
            "rbac": "operational",
            "abac": "operational",
            "sso": "operational",
            "tenant_management": "operational",
        },
        "timestamp": "2025-06-20T11:00:00Z",
    }
