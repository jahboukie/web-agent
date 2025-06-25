"""
E2E Tests: Multi-Tenant Operations
Test tenant isolation, conflicting resources, tenant-specific encryption, and per-tenant rate limiting
"""

from unittest.mock import patch

import pytest

from app.core.zero_knowledge import zero_knowledge_service
from app.services.rbac_service import rbac_service
from app.services.task_service import TaskService
from app.services.tenant_service import tenant_service
from app.services.user_service import UserService


class TestTenantIsolation:
    """Test complete tenant isolation and data segregation."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_data_isolation(self, test_db, test_client):
        """
        Test complete data isolation between tenants.

        Validates that tenants cannot access each other's data through any means.
        """
        # Create multiple tenants with different configurations
        tenant_configs = [
            {
                "name": "Healthcare Corp",
                "domain": "healthcare.example.com",
                "settings": {
                    "data_retention_days": 2555,  # 7 years for HIPAA
                    "encryption_required": True,
                    "compliance_level": "hipaa",
                    "audit_level": "detailed",
                },
            },
            {
                "name": "Financial Services Inc",
                "domain": "finserv.example.com",
                "settings": {
                    "data_retention_days": 3650,  # 10 years for financial
                    "encryption_required": True,
                    "compliance_level": "sox",
                    "audit_level": "comprehensive",
                },
            },
            {
                "name": "Tech Startup LLC",
                "domain": "startup.example.com",
                "settings": {
                    "data_retention_days": 365,  # 1 year
                    "encryption_required": False,
                    "compliance_level": "basic",
                    "audit_level": "standard",
                },
            },
        ]

        # Create tenants
        tenants = {}
        for config in tenant_configs:
            tenant = await tenant_service.create_tenant(
                test_db,
                name=config["name"],
                domain=config["domain"],
                settings=config["settings"],
            )
            tenants[config["name"]] = tenant

        # Create users for each tenant
        tenant_users = {}
        for tenant_name, tenant in tenants.items():
            # Create admin user for tenant
            admin_user = await UserService.create_user(
                test_db,
                email=f"admin@{tenant.domain}",
                username=f"{tenant_name.lower().replace(' ', '_')}_admin",
                password="TenantAdmin123!",
                full_name=f"{tenant_name} Administrator",
                tenant_id=tenant.id,
            )

            # Create regular user for tenant
            regular_user = await UserService.create_user(
                test_db,
                email=f"user@{tenant.domain}",
                username=f"{tenant_name.lower().replace(' ', '_')}_user",
                password="TenantUser123!",
                full_name=f"{tenant_name} User",
                tenant_id=tenant.id,
            )

            tenant_users[tenant_name] = {
                "admin": admin_user,
                "user": regular_user,
                "tenant": tenant,
            }

        await test_db.commit()

        # Create tenant-specific data
        tenant_data = {}
        for tenant_name, users in tenant_users.items():
            # Create tasks for each tenant
            tasks = []
            for i in range(5):
                task = await TaskService.create_task(
                    test_db,
                    user_id=users["user"].id,
                    task_data={
                        "title": f"{tenant_name} Confidential Task {i + 1}",
                        "description": f"Sensitive data for {tenant_name} - Task {i + 1}",
                        "goal": f"Process confidential {tenant_name} information",
                        "target_url": f"https://{users['tenant'].domain}/internal/task{i + 1}",
                    },
                )
                tasks.append(task)

            tenant_data[tenant_name] = {"tasks": tasks}

        await test_db.commit()

        # Test cross-tenant access attempts
        for accessing_tenant, accessing_users in tenant_users.items():
            for target_tenant, target_data in tenant_data.items():
                if accessing_tenant == target_tenant:
                    continue  # Skip same-tenant access

                # Attempt to access other tenant's tasks
                for task in target_data["tasks"]:
                    # Try with admin user from different tenant
                    admin_token = self._create_auth_token(accessing_users["admin"])
                    admin_headers = {"Authorization": f"Bearer {admin_token}"}

                    response = test_client.get(
                        f"/api/v1/tasks/{task.id}", headers=admin_headers
                    )

                    # Should not be able to access other tenant's data
                    assert (
                        response.status_code
                        in [
                            404,
                            403,
                        ]
                    ), f"{accessing_tenant} admin should not access {target_tenant} task {task.id}"

                    # Try with regular user from different tenant
                    user_token = self._create_auth_token(accessing_users["user"])
                    user_headers = {"Authorization": f"Bearer {user_token}"}

                    response = test_client.get(
                        f"/api/v1/tasks/{task.id}", headers=user_headers
                    )

                    assert (
                        response.status_code
                        in [
                            404,
                            403,
                        ]
                    ), f"{accessing_tenant} user should not access {target_tenant} task {task.id}"

        # Test tenant-specific queries return only tenant data
        for tenant_name, users in tenant_users.items():
            user_token = self._create_auth_token(users["user"])
            headers = {"Authorization": f"Bearer {user_token}"}

            # Get all tasks for user
            response = test_client.get("/api/v1/tasks/", headers=headers)
            assert response.status_code == 200

            tasks = response.json()

            # Should only return tasks from same tenant
            for task in tasks:
                assert (
                    tenant_name in task["title"]
                ), f"User from {tenant_name} received task from different tenant: {task['title']}"

                # Verify task belongs to same tenant user
                task_user_id = task["user_id"]
                assert (
                    task_user_id == users["user"].id
                ), f"Task user_id {task_user_id} doesn't match tenant user {users['user'].id}"

    def _create_auth_token(self, user):
        """Helper to create authentication token for user."""
        from app.core.security import create_access_token

        return create_access_token(data={"sub": str(user.id)})

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_conflicting_resource_names(self, test_db, test_client):
        """
        Test handling of conflicting resource names across tenants.

        Validates that resources with same names in different tenants don't conflict.
        """
        # Create two tenants
        tenant_a = await tenant_service.create_tenant(
            test_db,
            name="Company A",
            domain="company-a.com",
            settings={"namespace": "company_a"},
        )

        tenant_b = await tenant_service.create_tenant(
            test_db,
            name="Company B",
            domain="company-b.com",
            settings={"namespace": "company_b"},
        )

        # Create users for each tenant
        user_a = await UserService.create_user(
            test_db,
            email="user@company-a.com",
            username="company_a_user",
            password="UserA123!",
            full_name="Company A User",
            tenant_id=tenant_a.id,
        )

        user_b = await UserService.create_user(
            test_db,
            email="user@company-b.com",
            username="company_b_user",
            password="UserB123!",
            full_name="Company B User",
            tenant_id=tenant_b.id,
        )

        await test_db.commit()

        # Create resources with identical names in both tenants
        conflicting_resources = [
            {
                "type": "task",
                "name": "Production Deployment",
                "data": {
                    "title": "Production Deployment",
                    "description": "Deploy to production environment",
                    "goal": "Complete production deployment",
                },
            },
            {
                "type": "role",
                "name": "Project Manager",
                "data": {
                    "name": "Project Manager",
                    "description": "Manages project resources and timeline",
                    "permissions": ["tasks:read", "tasks:create", "users:read"],
                },
            },
        ]

        created_resources = {"tenant_a": {}, "tenant_b": {}}

        for resource in conflicting_resources:
            if resource["type"] == "task":
                # Create task for tenant A
                task_a = await TaskService.create_task(
                    test_db, user_id=user_a.id, task_data=resource["data"]
                )
                created_resources["tenant_a"]["task"] = task_a

                # Create task with same name for tenant B
                task_b = await TaskService.create_task(
                    test_db, user_id=user_b.id, task_data=resource["data"]
                )
                created_resources["tenant_b"]["task"] = task_b

            elif resource["type"] == "role":
                # Create role for tenant A
                role_a = await rbac_service.create_role(
                    test_db,
                    name=resource["data"]["name"],
                    description=resource["data"]["description"],
                    permissions=resource["data"]["permissions"],
                    tenant_id=tenant_a.id,
                )
                created_resources["tenant_a"]["role"] = role_a

                # Create role with same name for tenant B
                role_b = await rbac_service.create_role(
                    test_db,
                    name=resource["data"]["name"],
                    description=resource["data"]["description"],
                    permissions=resource["data"]["permissions"],
                    tenant_id=tenant_b.id,
                )
                created_resources["tenant_b"]["role"] = role_b

        await test_db.commit()

        # Verify resources are properly isolated despite same names
        # Test task isolation
        token_a = self._create_auth_token(user_a)
        token_b = self._create_auth_token(user_b)

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A should only see their task
        response_a = test_client.get("/api/v1/tasks/", headers=headers_a)
        assert response_a.status_code == 200
        tasks_a = response_a.json()
        assert len(tasks_a) == 1
        assert tasks_a[0]["id"] == created_resources["tenant_a"]["task"].id

        # User B should only see their task
        response_b = test_client.get("/api/v1/tasks/", headers=headers_b)
        assert response_b.status_code == 200
        tasks_b = response_b.json()
        assert len(tasks_b) == 1
        assert tasks_b[0]["id"] == created_resources["tenant_b"]["task"].id

        # Verify tasks have different IDs despite same names
        assert (
            created_resources["tenant_a"]["task"].id
            != created_resources["tenant_b"]["task"].id
        )
        assert (
            created_resources["tenant_a"]["role"].id
            != created_resources["tenant_b"]["role"].id
        )

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_tenant_specific_configurations(self, test_db):
        """
        Test tenant-specific configurations and settings.

        Validates that each tenant can have different configurations.
        """
        # Create tenants with different configurations
        tenant_configs = [
            {
                "name": "High Security Tenant",
                "settings": {
                    "session_timeout_minutes": 15,
                    "max_concurrent_sessions": 1,
                    "require_mfa": True,
                    "password_policy": {
                        "min_length": 16,
                        "require_special_chars": True,
                        "require_numbers": True,
                        "require_uppercase": True,
                    },
                    "data_retention_days": 2555,
                    "encryption_algorithm": "AES-256-GCM",
                },
            },
            {
                "name": "Standard Tenant",
                "settings": {
                    "session_timeout_minutes": 60,
                    "max_concurrent_sessions": 5,
                    "require_mfa": False,
                    "password_policy": {
                        "min_length": 8,
                        "require_special_chars": False,
                        "require_numbers": True,
                        "require_uppercase": False,
                    },
                    "data_retention_days": 365,
                    "encryption_algorithm": "AES-128-GCM",
                },
            },
        ]

        created_tenants = {}
        for config in tenant_configs:
            tenant = await tenant_service.create_tenant(
                test_db,
                name=config["name"],
                domain=f"{config['name'].lower().replace(' ', '-')}.example.com",
                settings=config["settings"],
            )
            created_tenants[config["name"]] = tenant

        await test_db.commit()

        # Verify tenant-specific settings are applied
        for tenant_name, tenant in created_tenants.items():
            tenant_settings = await tenant_service.get_tenant_settings(
                test_db, tenant.id
            )

            original_config = next(
                c for c in tenant_configs if c["name"] == tenant_name
            )
            expected_settings = original_config["settings"]

            # Verify each setting is correctly stored and retrieved
            for setting_key, expected_value in expected_settings.items():
                assert (
                    setting_key in tenant_settings
                ), f"Setting '{setting_key}' missing for tenant {tenant_name}"

                assert tenant_settings[setting_key] == expected_value, (
                    f"Setting '{setting_key}' mismatch for tenant {tenant_name}: "
                    f"expected {expected_value}, got {tenant_settings[setting_key]}"
                )

        # Test that settings are enforced per tenant
        high_security_tenant = created_tenants["High Security Tenant"]
        standard_tenant = created_tenants["Standard Tenant"]

        # Create users in each tenant
        high_sec_user = await UserService.create_user(
            test_db,
            email="user@high-security-tenant.example.com",
            username="high_sec_user",
            password="HighSecurityPassword123!@#",  # Meets high security requirements
            full_name="High Security User",
            tenant_id=high_security_tenant.id,
        )

        # Attempt to create user with weak password in high security tenant
        with pytest.raises(Exception) as exc_info:
            await UserService.create_user(
                test_db,
                email="weak@high-security-tenant.example.com",
                username="weak_user",
                password="weak123",  # Doesn't meet high security requirements
                full_name="Weak Password User",
                tenant_id=high_security_tenant.id,
            )

        # Should fail due to password policy
        assert "password" in str(exc_info.value).lower()

        # Same weak password should be acceptable in standard tenant
        standard_user = await UserService.create_user(
            test_db,
            email="user@standard-tenant.example.com",
            username="standard_user",
            password="weak123",  # Acceptable for standard tenant
            full_name="Standard User",
            tenant_id=standard_tenant.id,
        )

        assert standard_user is not None


class TestTenantSpecificEncryption:
    """Test tenant-specific encryption keys and algorithms."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_tenant_encryption_isolation(self, test_db):
        """
        Test that each tenant has separate encryption keys.

        Validates that tenant data cannot be decrypted with other tenant's keys.
        """
        # Create tenants with different encryption requirements
        tenant_gov = await tenant_service.create_tenant(
            test_db,
            name="Government Agency",
            domain="gov.agency.example.com",
            settings={
                "encryption_algorithm": "AES-256-GCM",
                "key_rotation_days": 30,
                "compliance_level": "fedramp_high",
                "encryption_required": True,
            },
        )

        tenant_corp = await tenant_service.create_tenant(
            test_db,
            name="Corporate Client",
            domain="corp.client.example.com",
            settings={
                "encryption_algorithm": "ChaCha20Poly1305",
                "key_rotation_days": 90,
                "compliance_level": "soc2_type2",
                "encryption_required": True,
            },
        )

        await test_db.commit()

        # Generate tenant-specific master keys
        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            # Mock different keys for each tenant
            mock_hsm.generate_tenant_master_key.side_effect = [
                {
                    "key_id": "gov_master_key_123",
                    "algorithm": "AES-256-GCM",
                    "tenant_id": tenant_gov.id,
                },
                {
                    "key_id": "corp_master_key_456",
                    "algorithm": "ChaCha20Poly1305",
                    "tenant_id": tenant_corp.id,
                },
            ]

            # Generate keys for each tenant
            gov_key = await zero_knowledge_service.generate_tenant_master_key(
                test_db, tenant_gov.id
            )

            corp_key = await zero_knowledge_service.generate_tenant_master_key(
                test_db, tenant_corp.id
            )

        # Verify different keys were generated
        assert gov_key["key_id"] != corp_key["key_id"]
        assert gov_key["algorithm"] != corp_key["algorithm"]

        # Test data encryption with tenant-specific keys
        gov_data = {
            "classification": "top_secret",
            "agency": "NSA",
            "operation": "classified_operation_alpha",
        }

        corp_data = {
            "classification": "confidential",
            "department": "HR",
            "employee_records": "sensitive_hr_data",
        }

        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            # Mock encryption with different tenant keys
            mock_hsm.encrypt_with_tenant_key.side_effect = [
                "encrypted_gov_data_with_gov_key",
                "encrypted_corp_data_with_corp_key",
            ]

            # Encrypt data for each tenant
            encrypted_gov = await zero_knowledge_service.encrypt_tenant_data(
                test_db, tenant_gov.id, gov_data
            )

            encrypted_corp = await zero_knowledge_service.encrypt_tenant_data(
                test_db, tenant_corp.id, corp_data
            )

        # Verify different encryption results
        assert encrypted_gov != encrypted_corp

        # Test cross-tenant decryption attempts (should fail)
        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            # Mock decryption failure when using wrong tenant key
            mock_hsm.decrypt_with_tenant_key.side_effect = Exception(
                "Decryption failed: Invalid key"
            )

            # Attempt to decrypt government data with corporate key
            with pytest.raises(Exception) as exc_info:
                await zero_knowledge_service.decrypt_tenant_data(
                    test_db,
                    tenant_corp.id,
                    encrypted_gov,  # Wrong tenant ID
                )

            assert "decryption" in str(exc_info.value).lower()

            # Attempt to decrypt corporate data with government key
            with pytest.raises(Exception) as exc_info:
                await zero_knowledge_service.decrypt_tenant_data(
                    test_db,
                    tenant_gov.id,
                    encrypted_corp,  # Wrong tenant ID
                )

            assert "decryption" in str(exc_info.value).lower()


class TestPerTenantRateLimiting:
    """Test per-tenant rate limiting configurations."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_tenant_specific_rate_limits(self, test_db, test_client):
        """
        Test per-tenant rate limiting configurations.

        Validates that different tenants can have different rate limits.
        """
        # Create tenants with different rate limiting configurations
        tenant_premium = await tenant_service.create_tenant(
            test_db,
            name="Premium Tenant",
            domain="premium.example.com",
            settings={
                "rate_limits": {
                    "api_requests_per_minute": 1000,
                    "concurrent_requests": 50,
                    "burst_allowance": 200,
                },
                "subscription_tier": "enterprise",
            },
        )

        tenant_basic = await tenant_service.create_tenant(
            test_db,
            name="Basic Tenant",
            domain="basic.example.com",
            settings={
                "rate_limits": {
                    "api_requests_per_minute": 100,
                    "concurrent_requests": 10,
                    "burst_allowance": 20,
                },
                "subscription_tier": "basic",
            },
        )

        # Create users for each tenant
        premium_user = await UserService.create_user(
            test_db,
            email="user@premium.example.com",
            username="premium_user",
            password="PremiumUser123!",
            full_name="Premium User",
            tenant_id=tenant_premium.id,
        )

        basic_user = await UserService.create_user(
            test_db,
            email="user@basic.example.com",
            username="basic_user",
            password="BasicUser123!",
            full_name="Basic User",
            tenant_id=tenant_basic.id,
        )

        await test_db.commit()

        # Test rate limiting for basic tenant (should hit limits quickly)
        basic_token = self._create_auth_token(basic_user)
        basic_headers = {"Authorization": f"Bearer {basic_token}"}

        basic_responses = []
        for i in range(150):  # Exceed basic tenant limit
            response = test_client.get("/api/v1/tasks/", headers=basic_headers)
            basic_responses.append(
                {"request": i + 1, "status_code": response.status_code}
            )

            # Stop if rate limited
            if response.status_code == 429:
                break

        # Basic tenant should hit rate limits
        rate_limited_basic = [r for r in basic_responses if r["status_code"] == 429]
        assert len(rate_limited_basic) > 0, "Basic tenant should hit rate limits"

        # Test rate limiting for premium tenant (should handle more requests)
        premium_token = self._create_auth_token(premium_user)
        premium_headers = {"Authorization": f"Bearer {premium_token}"}

        premium_responses = []
        for i in range(150):  # Same number of requests
            response = test_client.get("/api/v1/tasks/", headers=premium_headers)
            premium_responses.append(
                {"request": i + 1, "status_code": response.status_code}
            )

            # Stop if rate limited
            if response.status_code == 429:
                break

        # Premium tenant should handle more requests before rate limiting
        successful_premium = [r for r in premium_responses if r["status_code"] == 200]
        successful_basic = [r for r in basic_responses if r["status_code"] == 200]

        assert (
            len(successful_premium) > len(successful_basic)
        ), f"Premium tenant should handle more requests: {len(successful_premium)} vs {len(successful_basic)}"

    def _create_auth_token(self, user):
        """Helper to create authentication token for user."""
        from app.core.security import create_access_token

        return create_access_token(data={"sub": str(user.id)})

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_tenant_resource_quotas(self, test_db):
        """
        Test tenant-specific resource quotas and enforcement.

        Validates that tenants cannot exceed their allocated resources.
        """
        # Create tenants with different resource quotas
        tenant_small = await tenant_service.create_tenant(
            test_db,
            name="Small Business",
            domain="small.business.com",
            settings={
                "resource_quotas": {
                    "max_tasks": 100,
                    "max_users": 10,
                    "max_storage_mb": 1000,
                    "max_api_calls_per_day": 10000,
                }
            },
        )

        tenant_large = await tenant_service.create_tenant(
            test_db,
            name="Large Enterprise",
            domain="large.enterprise.com",
            settings={
                "resource_quotas": {
                    "max_tasks": 10000,
                    "max_users": 1000,
                    "max_storage_mb": 100000,
                    "max_api_calls_per_day": 1000000,
                }
            },
        )

        # Create user for small tenant
        small_user = await UserService.create_user(
            test_db,
            email="user@small.business.com",
            username="small_user",
            password="SmallUser123!",
            full_name="Small Business User",
            tenant_id=tenant_small.id,
        )

        await test_db.commit()

        # Test task creation quota enforcement
        created_tasks = []

        # Create tasks up to the limit
        for i in range(105):  # Try to exceed limit of 100
            try:
                task = await TaskService.create_task(
                    test_db,
                    user_id=small_user.id,
                    task_data={
                        "title": f"Task {i + 1}",
                        "description": f"Test task {i + 1}",
                        "goal": f"Complete task {i + 1}",
                    },
                )
                created_tasks.append(task)

            except Exception as e:
                # Should hit quota limit
                if "quota" in str(e).lower() or "limit" in str(e).lower():
                    break
                else:
                    raise  # Re-raise if it's not a quota error

        # Should not be able to create more than quota allows
        assert (
            len(created_tasks) <= 100
        ), f"Should not exceed task quota of 100, created {len(created_tasks)}"

        # Test user creation quota
        created_users = [small_user]  # Already have one user

        for i in range(15):  # Try to exceed limit of 10 users
            try:
                user = await UserService.create_user(
                    test_db,
                    email=f"user{i + 2}@small.business.com",
                    username=f"small_user_{i + 2}",
                    password="SmallUser123!",
                    full_name=f"Small Business User {i + 2}",
                    tenant_id=tenant_small.id,
                )
                created_users.append(user)

            except Exception as e:
                # Should hit quota limit
                if "quota" in str(e).lower() or "limit" in str(e).lower():
                    break
                else:
                    raise

        # Should not exceed user quota
        assert (
            len(created_users) <= 10
        ), f"Should not exceed user quota of 10, created {len(created_users)}"
