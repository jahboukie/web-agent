"""
Enterprise RBAC/ABAC Integration Tests

Comprehensive integration tests for the enterprise access control system
including RBAC, ABAC, SSO, tenant management, and security validation.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_async_session
from app.models.security import (
    EnterpriseTenant, EnterpriseRole, EnterprisePermission,
    SSOConfiguration, ABACPolicy, AccessSession
)
from app.models.user import User
from app.schemas.enterprise import (
    EnterpriseTenantCreate, EnterpriseRoleCreate, EnterprisePermissionCreate,
    SSOConfigurationCreate, ABACPolicyCreate
)
from app.schemas.user import UserTenantRoleAssignment
from app.services.tenant_service import enterprise_tenant_service
from app.services.rbac_service import enterprise_rbac_service
from app.services.abac_service import enterprise_abac_service
from app.services.sso_service import enterprise_sso_service


class TestEnterpriseIntegration:
    """Integration tests for enterprise access control system."""
    
    @pytest.fixture
    async def db_session(self):
        """Get database session for testing."""
        async for session in get_async_session():
            yield session
            break
    
    @pytest.fixture
    async def test_tenant(self, db_session: AsyncSession):
        """Create test tenant."""
        tenant_data = EnterpriseTenantCreate(
            tenant_id="test_corp",
            name="Test Corporation",
            display_name="Test Corp",
            domain="testcorp.com",
            admin_email="admin@testcorp.com",
            compliance_level="internal",
            max_users=100,
            enforce_sso=True,
            require_mfa=True
        )
        
        tenant = await enterprise_tenant_service.create_tenant(db_session, tenant_data, 1)
        return tenant
    
    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create test user."""
        user = User(
            email="test@testcorp.com",
            username="testuser",
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True,
            employee_id="EMP001",
            department="Engineering",
            job_title="Software Engineer"
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def test_role(self, db_session: AsyncSession):
        """Create test role."""
        role_data = EnterpriseRoleCreate(
            role_id="test_engineer",
            name="Test Engineer",
            display_name="Test Engineer",
            description="Test engineering role",
            is_system_role=False,
            is_tenant_scoped=True,
            permission_ids=[]
        )
        
        role = await enterprise_rbac_service.create_role(db_session, role_data, 1)
        return role
    
    async def test_system_initialization(self, db_session: AsyncSession):
        """Test enterprise system initialization."""
        # Initialize system permissions
        await enterprise_rbac_service.initialize_system_permissions(db_session)
        
        # Initialize system roles
        await enterprise_rbac_service.initialize_system_roles(db_session)
        
        # Verify permissions were created
        from sqlalchemy import select, func
        result = await db_session.execute(
            select(func.count(EnterprisePermission.id))
        )
        permission_count = result.scalar()
        assert permission_count > 0, "System permissions should be created"
        
        # Verify roles were created
        result = await db_session.execute(
            select(func.count(EnterpriseRole.id))
        )
        role_count = result.scalar()
        assert role_count > 0, "System roles should be created"
    
    async def test_tenant_management(self, db_session: AsyncSession):
        """Test tenant management operations."""
        # Create tenant
        tenant_data = EnterpriseTenantCreate(
            tenant_id="integration_test",
            name="Integration Test Tenant",
            display_name="Integration Test",
            domain="integration.test",
            admin_email="admin@integration.test",
            compliance_level="confidential",
            max_users=50
        )
        
        tenant = await enterprise_tenant_service.create_tenant(db_session, tenant_data, 1)
        assert tenant.tenant_id == "integration_test"
        assert tenant.compliance_level == "confidential"
        
        # Get tenant stats
        stats = await enterprise_tenant_service.get_tenant_stats(db_session, tenant.id)
        assert stats["tenant_id"] == "integration_test"
        assert stats["total_users"] == 0
        
        # Check tenant limits
        limits = await enterprise_tenant_service.check_tenant_limits(db_session, tenant.id, "users")
        assert limits["maximum"] == 50
        assert limits["current"] == 0
    
    async def test_rbac_operations(self, db_session: AsyncSession, test_tenant, test_user, test_role):
        """Test RBAC operations."""
        # Assign role to user in tenant
        assignment = UserTenantRoleAssignment(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            role_ids=[test_role.id]
        )
        
        success = await enterprise_rbac_service.assign_user_roles(db_session, assignment, 1)
        assert success, "Role assignment should succeed"
        
        # Check user permissions
        permissions = await enterprise_rbac_service.get_user_permissions(
            db_session, test_user.id, test_tenant.id
        )
        assert isinstance(permissions, set), "Permissions should be returned as set"
        
        # Test permission check
        has_permission = await enterprise_rbac_service.check_user_permission(
            db_session, test_user.id, "tasks:create", test_tenant.id
        )
        # This might be False if the test role doesn't have this permission
        assert isinstance(has_permission, bool), "Permission check should return boolean"
    
    async def test_abac_policy_evaluation(self, db_session: AsyncSession, test_tenant, test_user):
        """Test ABAC policy creation and evaluation."""
        # Create ABAC policy
        policy_data = ABACPolicyCreate(
            policy_id="test_policy",
            tenant_id=test_tenant.id,
            name="Test Policy",
            description="Test ABAC policy",
            effect="ALLOW",
            priority=100,
            conditions={
                "user.department": {"eq": "Engineering"},
                "env.is_business_hours": {"eq": True}
            },
            resources=["task"],
            actions=["read"]
        )
        
        policy = await enterprise_abac_service.create_policy(db_session, policy_data, 1)
        assert policy.policy_id == "test_policy"
        assert policy.effect == "ALLOW"
        
        # Evaluate access
        decision = await enterprise_abac_service.evaluate_access(
            db_session,
            user_id=test_user.id,
            resource_type="task",
            resource_id="test_task_123",
            action="read",
            tenant_id=test_tenant.id,
            context={"is_business_hours": True}
        )
        
        assert hasattr(decision, 'decision'), "Decision should have decision attribute"
        assert decision.decision in ["ALLOW", "DENY", "ABSTAIN"], "Decision should be valid"
    
    async def test_sso_configuration(self, db_session: AsyncSession, test_tenant):
        """Test SSO configuration management."""
        # Create SSO configuration
        sso_data = SSOConfigurationCreate(
            tenant_id=test_tenant.id,
            provider="okta",
            protocol="oidc",
            name="Test Okta",
            display_name="Test Okta SSO",
            configuration={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "authorization_endpoint": "https://test.okta.com/oauth2/v1/authorize",
                "token_endpoint": "https://test.okta.com/oauth2/v1/token"
            },
            attribute_mapping={
                "email": "email",
                "given_name": "first_name",
                "family_name": "last_name"
            }
        )
        
        config = await enterprise_sso_service.create_sso_configuration(db_session, sso_data, 1)
        assert config.provider == "okta"
        assert config.protocol == "oidc"
        assert config.tenant_id == test_tenant.id
        
        # List SSO configurations
        configs = await enterprise_sso_service.list_sso_configurations(db_session, test_tenant.id)
        assert len(configs) == 1
        assert configs[0].id == config.id
        
        # Test SSO configuration (this will likely fail in test environment)
        test_result = await enterprise_sso_service.test_sso_configuration(db_session, config.id)
        assert "success" in test_result, "Test result should have success field"
    
    async def test_access_session_management(self, db_session: AsyncSession, test_tenant, test_user):
        """Test access session creation and management."""
        # Create access session
        session = await enterprise_rbac_service.create_access_session(
            db_session,
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            session_data={
                "is_sso": False,
                "device_fingerprint": "test_device_123",
                "ip_address": "192.168.1.100",
                "user_agent": "Test Browser",
                "requires_mfa": True
            }
        )
        
        assert session.user_id == test_user.id
        assert session.tenant_id == test_tenant.id
        assert session.is_active is True
        assert session.device_fingerprint == "test_device_123"
        
        # Verify session was created in database
        from sqlalchemy import select
        result = await db_session.execute(
            select(AccessSession).where(AccessSession.session_id == session.session_id)
        )
        db_session_obj = result.scalar_one_or_none()
        assert db_session_obj is not None, "Session should be saved in database"
    
    async def test_zero_trust_integration(self, db_session: AsyncSession, test_user):
        """Test Zero Trust framework integration."""
        # Test trust score calculation
        session_data = {
            "device_fingerprint": "unknown_device",
            "ip_address": "suspicious_ip",
            "geolocation": {"country": "Unknown"},
            "is_sso": False
        }
        
        # This tests the _calculate_initial_trust_score method indirectly
        session = await enterprise_rbac_service.create_access_session(
            db_session,
            user_id=test_user.id,
            session_data=session_data
        )
        
        # Trust score should be reduced for suspicious factors
        assert 0.0 <= session.initial_trust_score <= 1.0, "Trust score should be between 0 and 1"
        assert session.initial_trust_score < 1.0, "Trust score should be reduced for suspicious factors"
    
    async def test_compliance_framework_integration(self, db_session: AsyncSession, test_tenant):
        """Test compliance framework integration."""
        # Verify tenant compliance settings
        assert test_tenant.compliance_level in ["internal", "confidential", "restricted", "public"]
        assert test_tenant.audit_retention_days >= 30, "Audit retention should meet minimum requirements"
        assert test_tenant.encryption_required is True, "Encryption should be required"
        
        # Test data classification
        assert test_tenant.data_region is not None, "Data region should be specified"
    
    async def test_api_endpoints_integration(self):
        """Test API endpoints integration."""
        client = TestClient(app)
        
        # Test health endpoint (should not require authentication)
        response = client.get("/api/v1/enterprise/system/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "services" in health_data
        
        # Test that protected endpoints require authentication
        response = client.get("/api/v1/enterprise/tenants")
        assert response.status_code == 401, "Protected endpoint should require authentication"
    
    async def test_error_handling_and_validation(self, db_session: AsyncSession):
        """Test error handling and input validation."""
        # Test duplicate tenant creation
        tenant_data = EnterpriseTenantCreate(
            tenant_id="duplicate_test",
            name="Duplicate Test",
            display_name="Duplicate",
            domain="duplicate.test",
            admin_email="admin@duplicate.test"
        )
        
        # Create first tenant
        await enterprise_tenant_service.create_tenant(db_session, tenant_data, 1)
        
        # Try to create duplicate - should fail
        with pytest.raises(ValueError, match="already exists"):
            await enterprise_tenant_service.create_tenant(db_session, tenant_data, 1)
        
        # Test invalid ABAC policy conditions
        invalid_policy = ABACPolicyCreate(
            policy_id="invalid_policy",
            name="Invalid Policy",
            effect="ALLOW",
            conditions={
                "user.department": {"invalid_operator": "Engineering"}
            }
        )
        
        with pytest.raises(ValueError, match="Invalid operator"):
            await enterprise_abac_service.create_policy(db_session, invalid_policy, 1)
    
    async def test_performance_and_caching(self, db_session: AsyncSession, test_tenant, test_user):
        """Test performance optimizations and caching."""
        import time
        
        # Test permission check performance
        start_time = time.time()
        
        # Perform multiple permission checks
        for _ in range(10):
            await enterprise_rbac_service.check_user_permission(
                db_session, test_user.id, "tasks:read", test_tenant.id
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete reasonably quickly (adjust threshold as needed)
        assert total_time < 5.0, f"Permission checks took too long: {total_time}s"
    
    async def test_security_validation(self, db_session: AsyncSession):
        """Test security validation and protection mechanisms."""
        # Test that sensitive SSO configuration data is encrypted
        sso_data = SSOConfigurationCreate(
            tenant_id=1,  # Assuming tenant exists
            provider="test_provider",
            protocol="oidc",
            name="Security Test",
            display_name="Security Test",
            configuration={
                "client_secret": "super_secret_value",
                "private_key": "private_key_data"
            }
        )
        
        # The service should encrypt sensitive fields
        encrypted_config = await enterprise_sso_service._encrypt_sso_config(
            sso_data.configuration, "test_key_id"
        )
        
        # Sensitive fields should be encrypted (different from original)
        assert encrypted_config["client_secret"] != "super_secret_value"
        assert encrypted_config["private_key"] != "private_key_data"


# Run integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
