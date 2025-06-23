"""
Enterprise RBAC/ABAC Access Control Engine

Comprehensive Role-Based and Attribute-Based Access Control system
with enterprise SSO integration and fine-grained permissions.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any

from app.core.logging import get_logger
from app.schemas.user import AccessContext, ThreatLevel

logger = get_logger(__name__)


class Permission(str, Enum):
    """Granular system permissions."""

    # User Management
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    USERS_MANAGE_ROLES = "users:manage_roles"

    # Task Management
    TASKS_CREATE = "tasks:create"
    TASKS_READ_OWN = "tasks:read_own"
    TASKS_READ_ALL = "tasks:read_all"
    TASKS_UPDATE_OWN = "tasks:update_own"
    TASKS_UPDATE_ALL = "tasks:update_all"
    TASKS_DELETE_OWN = "tasks:delete_own"
    TASKS_DELETE_ALL = "tasks:delete_all"
    TASKS_EXECUTE = "tasks:execute"
    TASKS_APPROVE = "tasks:approve"

    # Execution Plans
    PLANS_CREATE = "plans:create"
    PLANS_READ_OWN = "plans:read_own"
    PLANS_READ_ALL = "plans:read_all"
    PLANS_UPDATE_OWN = "plans:update_own"
    PLANS_UPDATE_ALL = "plans:update_all"
    PLANS_DELETE_OWN = "plans:delete_own"
    PLANS_DELETE_ALL = "plans:delete_all"
    PLANS_APPROVE = "plans:approve"
    PLANS_VALIDATE = "plans:validate"

    # Credentials Management
    CREDENTIALS_CREATE = "credentials:create"
    CREDENTIALS_READ_OWN = "credentials:read_own"
    CREDENTIALS_READ_ALL = "credentials:read_all"
    CREDENTIALS_UPDATE_OWN = "credentials:update_own"
    CREDENTIALS_UPDATE_ALL = "credentials:update_all"
    CREDENTIALS_DELETE_OWN = "credentials:delete_own"
    CREDENTIALS_DELETE_ALL = "credentials:delete_all"

    # Security Management
    SECURITY_POLICIES_READ = "security:policies:read"
    SECURITY_POLICIES_WRITE = "security:policies:write"
    SECURITY_AUDIT_READ = "security:audit:read"
    SECURITY_INCIDENTS_MANAGE = "security:incidents:manage"
    SECURITY_MONITORING_ACCESS = "security:monitoring:access"

    # System Administration
    ADMIN_SYSTEM_CONFIG = "admin:system:config"
    ADMIN_TENANT_MANAGE = "admin:tenant:manage"
    ADMIN_COMPLIANCE_MANAGE = "admin:compliance:manage"
    ADMIN_SECURITY_CONFIG = "admin:security:config"
    ADMIN_BACKUP_RESTORE = "admin:backup:restore"
    SYSTEM_CONFIGURE = "system:configure"
    SYSTEM_MONITOR = "system:monitor"

    # Compliance and Audit
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_REPORTS_GENERATE = "compliance:reports:generate"
    AUDIT_LOGS_READ = "audit:logs:read"
    AUDIT_LOGS_EXPORT = "audit:logs:export"

    # API Access
    API_AUTOMATION = "api:automation"
    API_REPORTING = "api:reporting"
    API_ADMIN = "api:admin"

    # Wildcards
    ALL_PERMISSIONS = "*"
    TENANT_ADMIN = "tenant:*"
    USER_OWN_RESOURCES = "own:*"


class ResourceType(str, Enum):
    """System resource types for ABAC."""

    USER = "user"
    TASK = "task"
    EXECUTION_PLAN = "execution_plan"
    CREDENTIAL = "credential"
    SECURITY_POLICY = "security_policy"
    AUDIT_LOG = "audit_log"
    COMPLIANCE_REPORT = "compliance_report"
    TENANT = "tenant"
    SYSTEM = "system"


class ActionType(str, Enum):
    """Action types for ABAC."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    EXPORT = "export"
    CONFIGURE = "configure"


@dataclass
class Role:
    """Enterprise role definition."""

    role_id: str
    name: str
    description: str
    permissions: set[Permission]
    inherits_from: list[str] = field(default_factory=list)
    is_system_role: bool = True
    tenant_scoped: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str | None = None
    max_session_duration: int = 8  # hours
    requires_approval: bool = False
    risk_level: ThreatLevel = ThreatLevel.LOW


@dataclass
class Attribute:
    """ABAC attribute definition."""

    attribute_id: str
    name: str
    attribute_type: str  # "string", "number", "boolean", "datetime", "list"
    description: str
    required: bool = False
    possible_values: list[Any] | None = None
    validation_regex: str | None = None


@dataclass
class PolicyRule:
    """ABAC policy rule."""

    rule_id: str
    name: str
    description: str
    resource_type: ResourceType
    action: ActionType
    conditions: dict[str, Any]  # Attribute-based conditions
    effect: str = "ALLOW"  # "ALLOW" or "DENY"
    priority: int = 100
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AccessRequest:
    """Access control request."""

    request_id: str
    user_id: int
    tenant_id: str | None
    resource_type: ResourceType
    resource_id: str | None
    action: ActionType
    context: AccessContext
    attributes: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AccessDecision:
    """Access control decision."""

    request_id: str
    decision: str  # "ALLOW", "DENY", "ABSTAIN"
    reason: str
    applicable_policies: list[str] = field(default_factory=list)
    required_approvals: list[str] = field(default_factory=list)
    session_restrictions: dict[str, Any] = field(default_factory=dict)
    audit_required: bool = True
    decision_time: datetime = field(default_factory=datetime.utcnow)


class RBACEngine:
    """
    Enterprise Role-Based Access Control Engine

    Implements hierarchical role management with inheritance,
    fine-grained permissions, and tenant-scoped access control.
    """

    def __init__(self):
        self.roles = self._initialize_system_roles()
        self.user_roles = {}  # user_id -> List[role_id]
        self.role_hierarchy = {}  # role_id -> parent_role_ids

    def _initialize_system_roles(self) -> dict[str, Role]:
        """Initialize predefined system roles."""

        roles = {}

        # System Administrator - Full access
        roles["system_admin"] = Role(
            role_id="system_admin",
            name="System Administrator",
            description="Complete system administration access",
            permissions={Permission.ALL_PERMISSIONS},
            requires_approval=True,
            risk_level=ThreatLevel.CRITICAL,
            max_session_duration=4,
        )

        # Tenant Administrator - Tenant-scoped admin
        roles["tenant_admin"] = Role(
            role_id="tenant_admin",
            name="Tenant Administrator",
            description="Complete tenant administration access",
            permissions={
                Permission.TENANT_ADMIN,
                Permission.USERS_CREATE,
                Permission.USERS_READ,
                Permission.USERS_UPDATE,
                Permission.USERS_MANAGE_ROLES,
                Permission.TASKS_READ_ALL,
                Permission.TASKS_UPDATE_ALL,
                Permission.TASKS_APPROVE,
                Permission.PLANS_READ_ALL,
                Permission.PLANS_APPROVE,
                Permission.PLANS_VALIDATE,
                Permission.CREDENTIALS_READ_ALL,
                Permission.CREDENTIALS_UPDATE_ALL,
                Permission.SECURITY_POLICIES_READ,
                Permission.SECURITY_POLICIES_WRITE,
                Permission.COMPLIANCE_READ,
                Permission.COMPLIANCE_REPORTS_GENERATE,
                Permission.AUDIT_LOGS_READ,
            },
            tenant_scoped=True,
            risk_level=ThreatLevel.HIGH,
            max_session_duration=8,
        )

        # Automation Manager - Workflow management
        roles["automation_manager"] = Role(
            role_id="automation_manager",
            name="Automation Manager",
            description="Automation workflow management",
            permissions={
                Permission.TASKS_CREATE,
                Permission.TASKS_READ_ALL,
                Permission.TASKS_UPDATE_ALL,
                Permission.TASKS_EXECUTE,
                Permission.TASKS_APPROVE,
                Permission.PLANS_CREATE,
                Permission.PLANS_READ_ALL,
                Permission.PLANS_UPDATE_ALL,
                Permission.PLANS_APPROVE,
                Permission.PLANS_VALIDATE,
                Permission.CREDENTIALS_CREATE,
                Permission.CREDENTIALS_READ_OWN,
                Permission.CREDENTIALS_UPDATE_OWN,
                Permission.API_AUTOMATION,
            },
            tenant_scoped=True,
            risk_level=ThreatLevel.MEDIUM,
            max_session_duration=8,
        )

        # Security Analyst - Security monitoring
        roles["security_analyst"] = Role(
            role_id="security_analyst",
            name="Security Analyst",
            description="Security monitoring and incident response",
            permissions={
                Permission.SECURITY_POLICIES_READ,
                Permission.SECURITY_AUDIT_READ,
                Permission.SECURITY_INCIDENTS_MANAGE,
                Permission.SECURITY_MONITORING_ACCESS,
                Permission.AUDIT_LOGS_READ,
                Permission.COMPLIANCE_READ,
                Permission.TASKS_READ_ALL,
                Permission.PLANS_READ_ALL,
            },
            tenant_scoped=True,
            risk_level=ThreatLevel.MEDIUM,
            max_session_duration=12,
        )

        # Auditor - Read-only compliance access
        roles["auditor"] = Role(
            role_id="auditor",
            name="Auditor",
            description="Compliance and audit access",
            permissions={
                Permission.COMPLIANCE_READ,
                Permission.COMPLIANCE_REPORTS_GENERATE,
                Permission.AUDIT_LOGS_READ,
                Permission.AUDIT_LOGS_EXPORT,
                Permission.SECURITY_AUDIT_READ,
                Permission.TASKS_READ_ALL,
                Permission.PLANS_READ_ALL,
            },
            tenant_scoped=True,
            risk_level=ThreatLevel.LOW,
            max_session_duration=12,
        )

        # End User - Basic access
        roles["end_user"] = Role(
            role_id="end_user",
            name="End User",
            description="Basic user access for personal automation",
            permissions={
                Permission.TASKS_CREATE,
                Permission.TASKS_READ_OWN,
                Permission.TASKS_UPDATE_OWN,
                Permission.TASKS_DELETE_OWN,
                Permission.TASKS_EXECUTE,
                Permission.PLANS_CREATE,
                Permission.PLANS_READ_OWN,
                Permission.PLANS_UPDATE_OWN,
                Permission.PLANS_DELETE_OWN,
                Permission.CREDENTIALS_CREATE,
                Permission.CREDENTIALS_READ_OWN,
                Permission.CREDENTIALS_UPDATE_OWN,
                Permission.CREDENTIALS_DELETE_OWN,
                Permission.API_AUTOMATION,
            },
            tenant_scoped=True,
            risk_level=ThreatLevel.LOW,
            max_session_duration=12,
        )

        # Read-Only User - View access only
        roles["read_only"] = Role(
            role_id="read_only",
            name="Read-Only User",
            description="Read-only access for monitoring and reporting",
            permissions={
                Permission.TASKS_READ_OWN,
                Permission.PLANS_READ_OWN,
                Permission.API_REPORTING,
            },
            tenant_scoped=True,
            risk_level=ThreatLevel.LOW,
            max_session_duration=12,
        )

        return roles

    async def assign_role(
        self,
        user_id: int,
        role_id: str,
        assigned_by: int,
        tenant_id: str | None = None,
    ) -> bool:
        """Assign role to user with proper authorization."""

        try:
            # Verify role exists
            if role_id not in self.roles:
                logger.warning(f"Attempted to assign non-existent role: {role_id}")
                return False

            role = self.roles[role_id]

            # Check if assigner has permission to assign this role
            if not await self._can_assign_role(assigned_by, role_id, tenant_id):
                logger.warning(
                    f"User {assigned_by} cannot assign role {role_id} to user {user_id}"
                )
                return False

            # Initialize user roles if needed
            if user_id not in self.user_roles:
                self.user_roles[user_id] = []

            # Add role with tenant scope
            role_assignment = {
                "role_id": role_id,
                "tenant_id": tenant_id if role.tenant_scoped else None,
                "assigned_at": datetime.utcnow(),
                "assigned_by": assigned_by,
            }

            self.user_roles[user_id].append(role_assignment)

            logger.info(
                "Role assigned successfully",
                user_id=user_id,
                role_id=role_id,
                tenant_id=tenant_id,
                assigned_by=assigned_by,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to assign role: {str(e)}")
            return False

    async def check_permission(
        self,
        user_id: int,
        permission: Permission,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        context: AccessContext | None = None,
    ) -> bool:
        """Check if user has specific permission."""

        try:
            # Get user's effective permissions
            user_permissions = await self.get_user_permissions(user_id, tenant_id)

            # Check direct permission
            if permission in user_permissions:
                return True

            # Check wildcard permissions
            if Permission.ALL_PERMISSIONS in user_permissions:
                return True

            # Check tenant admin permission for tenant-scoped resources
            if tenant_id and Permission.TENANT_ADMIN in user_permissions:
                return True

            # Check "own resources" permission for resource owner
            if (
                resource_id
                and Permission.USER_OWN_RESOURCES in user_permissions
                and await self._is_resource_owner(user_id, resource_id)
            ):
                return True

            # Special permission mappings
            permission_str = permission.value

            # Check for broader permission patterns
            if ":" in permission_str:
                resource_type, action = permission_str.split(":", 1)
                broader_permission = f"{resource_type}:*"
                if Permission(broader_permission) in user_permissions:
                    return True

            return False

        except Exception as e:
            logger.error(f"Permission check failed: {str(e)}")
            return False

    async def get_user_permissions(
        self, user_id: int, tenant_id: str | None = None
    ) -> set[Permission]:
        """Get all effective permissions for user."""

        permissions = set()

        try:
            user_role_assignments = self.user_roles.get(user_id, [])

            for assignment in user_role_assignments:
                role_id = assignment["role_id"]
                assignment_tenant = assignment.get("tenant_id")

                # Skip tenant-specific roles if tenant doesn't match
                if assignment_tenant and assignment_tenant != tenant_id:
                    continue

                if role_id in self.roles:
                    role = self.roles[role_id]
                    permissions.update(role.permissions)

                    # Recursively add inherited permissions
                    inherited_permissions = await self._get_inherited_permissions(
                        role_id, tenant_id
                    )
                    permissions.update(inherited_permissions)

        except Exception as e:
            logger.error(f"Failed to get user permissions: {str(e)}")

        return permissions

    async def _get_inherited_permissions(
        self, role_id: str, tenant_id: str | None = None
    ) -> set[Permission]:
        """Get permissions from inherited roles."""

        permissions = set()

        try:
            if role_id in self.role_hierarchy:
                for parent_role_id in self.role_hierarchy[role_id]:
                    if parent_role_id in self.roles:
                        parent_role = self.roles[parent_role_id]
                        permissions.update(parent_role.permissions)

                        # Recursively get parent's inherited permissions
                        parent_inherited = await self._get_inherited_permissions(
                            parent_role_id, tenant_id
                        )
                        permissions.update(parent_inherited)

        except Exception as e:
            logger.error(f"Failed to get inherited permissions: {str(e)}")

        return permissions

    async def _can_assign_role(
        self, assigner_id: int, role_id: str, tenant_id: str | None = None
    ) -> bool:
        """Check if user can assign specific role."""

        # System admins can assign any role
        if await self.check_permission(assigner_id, Permission.ALL_PERMISSIONS):
            return True

        # Tenant admins can assign tenant-scoped roles
        if tenant_id and await self.check_permission(
            assigner_id, Permission.USERS_MANAGE_ROLES, tenant_id=tenant_id
        ):
            target_role = self.roles.get(role_id)
            if target_role and target_role.tenant_scoped:
                return True

        return False

    async def _is_resource_owner(self, user_id: int, resource_id: str) -> bool:
        """Check if user owns the resource."""

        # This would integrate with the database to check resource ownership
        # For now, we'll implement a simple check
        try:
            # Parse resource_id to determine ownership
            # Format: "resource_type:actual_id:owner_id"
            if ":" in resource_id:
                parts = resource_id.split(":")
                if len(parts) >= 3:
                    owner_id = int(parts[2])
                    return owner_id == user_id
        except (ValueError, IndexError):
            pass

        return False


class ABACEngine:
    """
    Attribute-Based Access Control Engine

    Implements fine-grained access control based on user, resource,
    environment, and action attributes with policy evaluation.
    """

    def __init__(self):
        self.attributes = self._initialize_attributes()
        self.policies = self._initialize_policies()

    def _initialize_attributes(self) -> dict[str, Attribute]:
        """Initialize system attributes for ABAC."""

        attributes = {}

        # User attributes
        attributes["user.role"] = Attribute(
            attribute_id="user.role",
            name="User Role",
            attribute_type="string",
            description="User's assigned role",
            required=True,
        )

        attributes["user.department"] = Attribute(
            attribute_id="user.department",
            name="User Department",
            attribute_type="string",
            description="User's department",
            required=False,
        )

        attributes["user.clearance_level"] = Attribute(
            attribute_id="user.clearance_level",
            name="Security Clearance Level",
            attribute_type="string",
            description="User's security clearance level",
            required=False,
            possible_values=["PUBLIC", "CONFIDENTIAL", "SECRET", "TOP_SECRET"],
        )

        attributes["user.trust_score"] = Attribute(
            attribute_id="user.trust_score",
            name="Trust Score",
            attribute_type="number",
            description="User's current trust score (0-100)",
            required=True,
        )

        # Resource attributes
        attributes["resource.classification"] = Attribute(
            attribute_id="resource.classification",
            name="Data Classification",
            attribute_type="string",
            description="Resource data classification level",
            required=True,
            possible_values=["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"],
        )

        attributes["resource.owner"] = Attribute(
            attribute_id="resource.owner",
            name="Resource Owner",
            attribute_type="string",
            description="Resource owner user ID",
            required=True,
        )

        attributes["resource.tenant"] = Attribute(
            attribute_id="resource.tenant",
            name="Resource Tenant",
            attribute_type="string",
            description="Resource tenant ID",
            required=False,
        )

        # Environment attributes
        attributes["env.time_of_day"] = Attribute(
            attribute_id="env.time_of_day",
            name="Time of Day",
            attribute_type="string",
            description="Current time of day",
            required=True,
            possible_values=["BUSINESS_HOURS", "AFTER_HOURS", "WEEKEND"],
        )

        attributes["env.location"] = Attribute(
            attribute_id="env.location",
            name="Access Location",
            attribute_type="string",
            description="Geographic location of access",
            required=True,
        )

        attributes["env.network_type"] = Attribute(
            attribute_id="env.network_type",
            name="Network Type",
            attribute_type="string",
            description="Type of network connection",
            required=True,
            possible_values=["CORPORATE", "VPN", "PUBLIC", "HOME"],
        )

        attributes["env.device_trust"] = Attribute(
            attribute_id="env.device_trust",
            name="Device Trust Level",
            attribute_type="string",
            description="Device trust level",
            required=True,
            possible_values=["TRUSTED", "MANAGED", "UNMANAGED", "UNTRUSTED"],
        )

        return attributes

    def _initialize_policies(self) -> dict[str, PolicyRule]:
        """Initialize default ABAC policies."""

        policies = {}

        # High-security resource access policy
        policies["high_security_access"] = PolicyRule(
            rule_id="high_security_access",
            name="High Security Resource Access",
            description="Restrict access to confidential resources",
            resource_type=ResourceType.TASK,
            action=ActionType.READ,
            conditions={
                "resource.classification": {"in": ["CONFIDENTIAL", "SECRET"]},
                "user.clearance_level": {"in": ["SECRET", "TOP_SECRET"]},
                "user.trust_score": {"gte": 80},
                "env.device_trust": {"in": ["TRUSTED", "MANAGED"]},
                "env.network_type": {"in": ["CORPORATE", "VPN"]},
            },
            effect="ALLOW",
            priority=200,
        )

        # Business hours restriction policy
        policies["business_hours_only"] = PolicyRule(
            rule_id="business_hours_only",
            name="Business Hours Access Only",
            description="Restrict sensitive operations to business hours",
            resource_type=ResourceType.EXECUTION_PLAN,
            action=ActionType.EXECUTE,
            conditions={
                "resource.classification": {"in": ["CONFIDENTIAL", "SECRET"]},
                "env.time_of_day": {"eq": "BUSINESS_HOURS"},
            },
            effect="ALLOW",
            priority=150,
        )

        # Deny untrusted device access
        policies["deny_untrusted_devices"] = PolicyRule(
            rule_id="deny_untrusted_devices",
            name="Deny Untrusted Device Access",
            description="Block access from untrusted devices",
            resource_type=ResourceType.SYSTEM,
            action=ActionType.READ,
            conditions={"env.device_trust": {"eq": "UNTRUSTED"}},
            effect="DENY",
            priority=300,
        )

        # Resource owner access policy
        policies["resource_owner_access"] = PolicyRule(
            rule_id="resource_owner_access",
            name="Resource Owner Access",
            description="Allow resource owners full access to their resources",
            resource_type=ResourceType.TASK,
            action=ActionType.UPDATE,
            conditions={"user.id": {"eq_attr": "resource.owner"}},
            effect="ALLOW",
            priority=100,
        )

        return policies

    async def evaluate_access(self, request: AccessRequest) -> AccessDecision:
        """Evaluate access request against ABAC policies."""

        try:
            # Collect all applicable policies
            applicable_policies = []
            for policy_id, policy in self.policies.items():
                if await self._policy_applies(policy, request):
                    applicable_policies.append(policy)

            # Sort policies by priority (higher priority first)
            applicable_policies.sort(key=lambda p: p.priority, reverse=True)

            # Evaluate policies in priority order
            final_decision = "ABSTAIN"
            decision_reason = "No applicable policies found"

            for policy in applicable_policies:
                if await self._evaluate_policy_conditions(policy, request):
                    final_decision = policy.effect
                    decision_reason = (
                        f"Policy '{policy.name}' evaluated to {policy.effect}"
                    )

                    # DENY takes precedence over ALLOW
                    if policy.effect == "DENY":
                        break

            # Default to DENY if no explicit ALLOW
            if final_decision == "ABSTAIN":
                final_decision = "DENY"
                decision_reason = "No explicit ALLOW policy found"

            decision = AccessDecision(
                request_id=request.request_id,
                decision=final_decision,
                reason=decision_reason,
                applicable_policies=[p.rule_id for p in applicable_policies],
            )

            logger.info(
                "ABAC access decision",
                request_id=request.request_id,
                user_id=request.user_id,
                resource_type=request.resource_type.value,
                action=request.action.value,
                decision=final_decision,
                policies_evaluated=len(applicable_policies),
            )

            return decision

        except Exception as e:
            logger.error(f"ABAC evaluation failed: {str(e)}")
            return AccessDecision(
                request_id=request.request_id,
                decision="DENY",
                reason=f"Evaluation error: {str(e)}",
            )

    async def _policy_applies(self, policy: PolicyRule, request: AccessRequest) -> bool:
        """Check if policy applies to the request."""

        # Check resource type match
        if policy.resource_type != request.resource_type:
            return False

        # Check action match
        if policy.action != request.action:
            return False

        # Policy applies
        return True

    async def _evaluate_policy_conditions(
        self, policy: PolicyRule, request: AccessRequest
    ) -> bool:
        """Evaluate policy conditions against request attributes."""

        try:
            # Combine request attributes with context attributes
            all_attributes = {
                **request.attributes,
                "user.id": request.user_id,
                "user.trust_score": request.context.risk_score
                * 100,  # Convert to 0-100 scale
                "env.device_trust": self._get_device_trust_level(
                    request.context.device_info
                ),
                "env.network_type": request.context.network_type.upper(),
                "env.time_of_day": self._get_time_of_day(),
                "env.location": request.context.geolocation.get("country", "UNKNOWN"),
            }

            # Evaluate each condition
            for attr_name, condition in policy.conditions.items():
                attr_value = all_attributes.get(attr_name)

                if not await self._evaluate_condition(
                    attr_value, condition, all_attributes
                ):
                    return False

            return True

        except Exception as e:
            logger.error(f"Condition evaluation failed: {str(e)}")
            return False

    async def _evaluate_condition(
        self, value: Any, condition: dict[str, Any], all_attributes: dict[str, Any]
    ) -> bool:
        """Evaluate individual condition."""

        try:
            for operator, expected in condition.items():
                if operator == "eq":
                    if value != expected:
                        return False
                elif operator == "ne":
                    if value == expected:
                        return False
                elif operator == "gt":
                    if not (isinstance(value, (int, float)) and value > expected):
                        return False
                elif operator == "gte":
                    if not (isinstance(value, (int, float)) and value >= expected):
                        return False
                elif operator == "lt":
                    if not (isinstance(value, (int, float)) and value < expected):
                        return False
                elif operator == "lte":
                    if not (isinstance(value, (int, float)) and value <= expected):
                        return False
                elif operator == "in":
                    if value not in expected:
                        return False
                elif operator == "not_in":
                    if value in expected:
                        return False
                elif operator == "eq_attr":
                    # Compare with another attribute
                    other_value = all_attributes.get(expected)
                    if value != other_value:
                        return False
                else:
                    logger.warning(f"Unknown condition operator: {operator}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Condition evaluation error: {str(e)}")
            return False

    def _get_device_trust_level(self, device_info) -> str:
        """Determine device trust level from device info."""

        if hasattr(device_info, "is_managed") and device_info.is_managed:
            return "MANAGED"
        elif hasattr(device_info, "trust_level"):
            if device_info.trust_level == ThreatLevel.LOW:
                return "TRUSTED"
            elif device_info.trust_level == ThreatLevel.MEDIUM:
                return "MANAGED"
            else:
                return "UNTRUSTED"
        else:
            return "UNMANAGED"

    def _get_time_of_day(self) -> str:
        """Determine time of day category."""

        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()

        # Weekend
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return "WEEKEND"

        # Business hours (9 AM to 6 PM)
        if 9 <= hour < 18:
            return "BUSINESS_HOURS"
        else:
            return "AFTER_HOURS"


class EnterpriseAccessControl:
    """
    Unified Enterprise Access Control System

    Combines RBAC and ABAC engines for comprehensive access control
    with enterprise SSO integration and audit capabilities.
    """

    def __init__(self):
        self.rbac_engine = RBACEngine()
        self.abac_engine = ABACEngine()
        self.access_cache = {}  # Cache for performance
        self.audit_log = []

    async def check_access(
        self,
        user_id: int,
        resource_type: ResourceType,
        action: ActionType,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        context: AccessContext | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> AccessDecision:
        """Comprehensive access control check using both RBAC and ABAC."""

        request_id = f"access_req_{uuid.uuid4().hex[:12]}"

        try:
            # Create access request
            request = AccessRequest(
                request_id=request_id,
                user_id=user_id,
                tenant_id=tenant_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                context=context
                or AccessContext(
                    ip_address="127.0.0.1",
                    geolocation={},
                    device_info=None,
                    network_type="corporate",
                    time_of_access=datetime.utcnow(),
                    user_agent="WebAgent/1.0",
                ),
                attributes=attributes or {},
            )

            # Check cache first
            cache_key = self._generate_cache_key(request)
            if cache_key in self.access_cache:
                cached_decision = self.access_cache[cache_key]
                if (
                    datetime.utcnow() - cached_decision.decision_time
                ).seconds < 300:  # 5 min cache
                    return cached_decision

            # Step 1: RBAC evaluation
            rbac_allowed = await self._check_rbac_access(request)

            # Step 2: ABAC evaluation
            abac_decision = await self.abac_engine.evaluate_access(request)

            # Step 3: Combine decisions
            final_decision = await self._combine_decisions(
                rbac_allowed, abac_decision, request
            )

            # Cache the decision
            self.access_cache[cache_key] = final_decision

            # Audit the access decision
            await self._audit_access_decision(request, final_decision)

            return final_decision

        except Exception as e:
            logger.error(f"Access control check failed: {str(e)}")
            return AccessDecision(
                request_id=request_id,
                decision="DENY",
                reason=f"Access control error: {str(e)}",
            )

    async def _check_rbac_access(self, request: AccessRequest) -> bool:
        """Check RBAC permissions."""

        # Map action to permission
        permission_map = {
            (ResourceType.TASK, ActionType.CREATE): Permission.TASKS_CREATE,
            (ResourceType.TASK, ActionType.READ): Permission.TASKS_READ_OWN,
            (ResourceType.TASK, ActionType.UPDATE): Permission.TASKS_UPDATE_OWN,
            (ResourceType.TASK, ActionType.DELETE): Permission.TASKS_DELETE_OWN,
            (ResourceType.TASK, ActionType.EXECUTE): Permission.TASKS_EXECUTE,
            (ResourceType.EXECUTION_PLAN, ActionType.CREATE): Permission.PLANS_CREATE,
            (ResourceType.EXECUTION_PLAN, ActionType.READ): Permission.PLANS_READ_OWN,
            (
                ResourceType.EXECUTION_PLAN,
                ActionType.UPDATE,
            ): Permission.PLANS_UPDATE_OWN,
            (
                ResourceType.EXECUTION_PLAN,
                ActionType.DELETE,
            ): Permission.PLANS_DELETE_OWN,
            (ResourceType.EXECUTION_PLAN, ActionType.APPROVE): Permission.PLANS_APPROVE,
            (ResourceType.CREDENTIAL, ActionType.CREATE): Permission.CREDENTIALS_CREATE,
            (ResourceType.CREDENTIAL, ActionType.READ): Permission.CREDENTIALS_READ_OWN,
            (
                ResourceType.CREDENTIAL,
                ActionType.UPDATE,
            ): Permission.CREDENTIALS_UPDATE_OWN,
            (
                ResourceType.CREDENTIAL,
                ActionType.DELETE,
            ): Permission.CREDENTIALS_DELETE_OWN,
            (ResourceType.AUDIT_LOG, ActionType.READ): Permission.AUDIT_LOGS_READ,
            (
                ResourceType.COMPLIANCE_REPORT,
                ActionType.READ,
            ): Permission.COMPLIANCE_READ,
        }

        key = (request.resource_type, request.action)
        required_permission = permission_map.get(key)

        if not required_permission:
            logger.warning(f"No RBAC permission mapping for {key}")
            return False

        return await self.rbac_engine.check_permission(
            request.user_id,
            required_permission,
            request.resource_id,
            request.tenant_id,
            request.context,
        )

    async def _combine_decisions(
        self, rbac_allowed: bool, abac_decision: AccessDecision, request: AccessRequest
    ) -> AccessDecision:
        """Combine RBAC and ABAC decisions."""

        # RBAC must allow first
        if not rbac_allowed:
            return AccessDecision(
                request_id=request.request_id,
                decision="DENY",
                reason="RBAC permission denied",
            )

        # If RBAC allows, use ABAC decision
        if abac_decision.decision == "DENY":
            return abac_decision

        # Both allow - final ALLOW
        return AccessDecision(
            request_id=request.request_id,
            decision="ALLOW",
            reason="Both RBAC and ABAC policies allow access",
            applicable_policies=abac_decision.applicable_policies,
        )

    def _generate_cache_key(self, request: AccessRequest) -> str:
        """Generate cache key for access request."""

        key_data = f"{request.user_id}:{request.resource_type.value}:{request.action.value}:{request.resource_id}:{request.tenant_id}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    async def _audit_access_decision(
        self, request: AccessRequest, decision: AccessDecision
    ) -> None:
        """Audit access control decisions."""

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request.request_id,
            "user_id": request.user_id,
            "tenant_id": request.tenant_id,
            "resource_type": request.resource_type.value,
            "resource_id": request.resource_id,
            "action": request.action.value,
            "decision": decision.decision,
            "reason": decision.reason,
            "applicable_policies": decision.applicable_policies,
            "ip_address": request.context.ip_address,
            "user_agent": request.context.user_agent,
        }

        self.audit_log.append(audit_entry)

        logger.info(
            "Access control decision audited",
            request_id=request.request_id,
            decision=decision.decision,
            user_id=request.user_id,
        )


# Global enterprise access control instance
enterprise_access_control = EnterpriseAccessControl()


def require_permission(permission: Permission):
    """Decorator for API endpoints to enforce permissions."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from request context
            # This would integrate with your authentication system
            user_id = kwargs.get("current_user_id")  # Adjust based on your auth system

            if not user_id:
                raise PermissionError("Authentication required")

            # Check permission
            has_permission = (
                await enterprise_access_control.rbac_engine.check_permission(
                    user_id, permission
                )
            )

            if not has_permission:
                raise PermissionError(f"Permission {permission.value} required")

            return await func(*args, **kwargs)

        return wrapper

    return decorator
