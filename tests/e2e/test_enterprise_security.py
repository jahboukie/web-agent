"""
E2E Tests: Enterprise Security
Tests for RBAC/ABAC, zero-knowledge encryption, tenant isolation, and session security
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.zero_knowledge import zero_knowledge_service
from app.services.abac_service import abac_service
from app.services.rbac_service import rbac_service
from app.services.tenant_service import tenant_service


class TestEnterpriseRBAC:
    """Test Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC)."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_rbac_permission_boundaries(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test permission boundaries across 5+ role combinations.

        Validates that users can only access resources they're authorized for.
        """
        # Define test roles with specific permissions
        roles_permissions = {
            "system_admin": [
                "users:create",
                "users:read",
                "users:update",
                "users:delete",
                "tenants:create",
                "tenants:read",
                "tenants:update",
                "tenants:delete",
                "security:read",
                "security:write",
                "audit:read",
            ],
            "tenant_admin": [
                "users:create",
                "users:read",
                "users:update",
                "tasks:create",
                "tasks:read",
                "tasks:update",
                "tasks:delete",
                "analytics:read",
            ],
            "security_manager": [
                "users:read",
                "security:read",
                "security:write",
                "audit:read",
                "compliance:read",
            ],
            "analyst": ["tasks:read", "analytics:read", "reports:create"],
            "basic_user": ["tasks:create", "tasks:read", "tasks:update"],
        }

        # Create roles in database
        created_roles = {}
        for role_name, permissions in roles_permissions.items():
            role = await rbac_service.create_role(
                test_db,
                name=role_name,
                description=f"Test role: {role_name}",
                permissions=permissions,
                tenant_id="test-enterprise",
            )
            created_roles[role_name] = role

        # Assign roles to test users
        await rbac_service.assign_role(
            test_db, test_users_db["admin"].id, created_roles["system_admin"].id
        )
        await rbac_service.assign_role(
            test_db, test_users_db["manager"].id, created_roles["tenant_admin"].id
        )
        await rbac_service.assign_role(
            test_db, test_users_db["auditor"].id, created_roles["security_manager"].id
        )
        await rbac_service.assign_role(
            test_db, test_users_db["user"].id, created_roles["basic_user"].id
        )

        # Test system admin access (should have full access)
        response = test_client.get(
            "/api/v1/enterprise/tenants", headers=auth_headers["admin"]
        )
        assert response.status_code == 200

        response = test_client.post(
            "/api/v1/users/",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "NewUser123!",
                "full_name": "New Test User",
            },
            headers=auth_headers["admin"],
        )
        assert response.status_code == 201

        # Test tenant admin access (limited to tenant operations)
        response = test_client.get("/api/v1/tasks/", headers=auth_headers["manager"])
        assert response.status_code == 200

        # Should NOT have access to system-wide tenant management
        response = test_client.get(
            "/api/v1/enterprise/tenants", headers=auth_headers["manager"]
        )
        assert response.status_code == 403

        # Test security manager access (read-only security)
        response = test_client.get(
            "/api/v1/security/audit-logs", headers=auth_headers["auditor"]
        )
        assert response.status_code == 200

        # Should NOT be able to create users
        response = test_client.post(
            "/api/v1/users/",
            json={
                "email": "unauthorized@test.com",
                "username": "unauthorized",
                "password": "Test123!",
                "full_name": "Unauthorized User",
            },
            headers=auth_headers["auditor"],
        )
        assert response.status_code == 403

        # Test basic user access (very limited)
        response = test_client.get("/api/v1/tasks/", headers=auth_headers["user"])
        assert response.status_code == 200

        # Should NOT have access to analytics
        response = test_client.get(
            "/api/v1/analytics/dashboard", headers=auth_headers["user"]
        )
        assert response.status_code == 403

        # Should NOT have access to security endpoints
        response = test_client.get(
            "/api/v1/security/audit-logs", headers=auth_headers["user"]
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_abac_contextual_access(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test Attribute-Based Access Control with contextual policies.

        Validates access based on user attributes, resource attributes, and environment.
        """
        user = test_users_db["manager"]

        # Create ABAC policy for time-based access
        time_policy = await abac_service.create_policy(
            test_db,
            name="business_hours_access",
            description="Allow access only during business hours",
            rules={
                "conditions": [
                    {
                        "attribute": "environment.time_of_day",
                        "operator": "between",
                        "value": ["09:00", "17:00"],
                    },
                    {
                        "attribute": "user.department",
                        "operator": "equals",
                        "value": "operations",
                    },
                ],
                "effect": "allow",
                "resources": ["tasks:execute", "plans:generate"],
            },
        )

        # Create location-based policy
        location_policy = await abac_service.create_policy(
            test_db,
            name="geo_restricted_access",
            description="Restrict access based on location",
            rules={
                "conditions": [
                    {
                        "attribute": "environment.country",
                        "operator": "in",
                        "value": ["US", "CA", "GB"],
                    },
                    {
                        "attribute": "user.security_clearance",
                        "operator": "gte",
                        "value": "standard",
                    },
                ],
                "effect": "allow",
                "resources": ["sensitive_data:read"],
            },
        )

        # Test access during business hours from allowed location
        with patch("app.security.abac_engine.get_current_context") as mock_context:
            mock_context.return_value = {
                "environment": {
                    "time_of_day": "14:30",  # 2:30 PM
                    "country": "US",
                    "ip_address": "192.168.1.100",
                },
                "user": {"department": "operations", "security_clearance": "standard"},
            }

            # Should allow task execution
            response = test_client.post(
                "/api/v1/tasks/1/execute",
                json={"execution_options": {"take_screenshots": True}},
                headers=auth_headers["manager"],
            )
            # Note: May return 404 if task doesn't exist, but should not be 403 (forbidden)
            assert response.status_code != 403

        # Test access outside business hours
        with patch("app.security.abac_engine.get_current_context") as mock_context:
            mock_context.return_value = {
                "environment": {"time_of_day": "22:30", "country": "US"},  # 10:30 PM
                "user": {"department": "operations", "security_clearance": "standard"},
            }

            # Should deny access
            response = test_client.post(
                "/api/v1/tasks/1/execute",
                json={"execution_options": {"take_screenshots": True}},
                headers=auth_headers["manager"],
            )
            assert response.status_code == 403
            assert "business hours" in response.json()["error"]["message"].lower()

        # Test access from restricted location
        with patch("app.security.abac_engine.get_current_context") as mock_context:
            mock_context.return_value = {
                "environment": {
                    "time_of_day": "14:30",
                    "country": "CN",  # Restricted country
                },
                "user": {"department": "operations", "security_clearance": "standard"},
            }

            # Should deny access to sensitive data
            response = test_client.get(
                "/api/v1/security/sensitive-data", headers=auth_headers["manager"]
            )
            assert response.status_code == 403
            assert "location" in response.json()["error"]["message"].lower()


class TestZeroKnowledgeEncryption:
    """Test zero-knowledge encryption and key management."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_encryption_keys_never_leave_hsm(self, test_db, test_users_db):
        """
        Validate zero-knowledge encryption: Confirm keys never leave HSM.

        Tests that private keys are never transmitted or stored in plaintext.
        """
        user = test_users_db["user"]

        # Mock HSM integration
        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.generate_key_pair.return_value = {
                "key_id": "hsm_key_12345",
                "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
                "private_key_ref": "hsm://key/12345",  # Reference only, not actual key  # pragma: allowlist secret
            }

            # Generate user encryption keys
            key_pair = await zero_knowledge_service.generate_user_keys(test_db, user.id)

            # Verify HSM was called for key generation
            mock_hsm.generate_key_pair.assert_called_once()

            # Verify only public key and reference are returned
            assert "public_key" in key_pair
            assert "private_key_ref" in key_pair
            assert "private_key" not in key_pair  # Private key should never be returned

            # Verify key reference points to HSM
            assert key_pair["private_key_ref"].startswith("hsm://")

        # Test encryption/decryption without exposing private key
        test_data = {"sensitive": "user_password", "account": "bank_details"}

        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.encrypt.return_value = "encrypted_data_blob_12345"
            mock_hsm.decrypt.return_value = json.dumps(test_data)

            # Encrypt data
            encrypted_data = await zero_knowledge_service.encrypt_user_data(
                test_db, user.id, test_data
            )

            # Verify encryption used HSM
            mock_hsm.encrypt.assert_called_once()
            assert encrypted_data != json.dumps(test_data)  # Should be encrypted

            # Decrypt data
            decrypted_data = await zero_knowledge_service.decrypt_user_data(
                test_db, user.id, encrypted_data
            )

            # Verify decryption used HSM
            mock_hsm.decrypt.assert_called_once()
            assert decrypted_data == test_data

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_key_rotation_impact(self, test_db, test_users_db):
        """
        Test key rotation impact on existing encrypted data.

        Validates that key rotation doesn't break access to existing data.
        """
        user = test_users_db["user"]

        # Create initial encrypted data
        original_data = {
            "secret": "original_value",
            "timestamp": str(datetime.utcnow()),
        }

        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.encrypt.return_value = "encrypted_original_data"

            encrypted_original = await zero_knowledge_service.encrypt_user_data(
                test_db, user.id, original_data
            )

        # Perform key rotation
        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.rotate_key.return_value = {
                "new_key_id": "hsm_key_67890",
                "old_key_id": "hsm_key_12345",
                "migration_required": True,
            }

            rotation_result = await zero_knowledge_service.rotate_user_keys(
                test_db, user.id
            )

            assert rotation_result["success"] is True
            assert "new_key_id" in rotation_result
            assert "migration_required" in rotation_result

        # Verify old data can still be decrypted during migration period
        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.decrypt.return_value = json.dumps(original_data)

            decrypted_data = await zero_knowledge_service.decrypt_user_data(
                test_db, user.id, encrypted_original
            )

            assert decrypted_data == original_data

        # Test new encryption uses new key
        new_data = {"secret": "new_value", "timestamp": str(datetime.utcnow())}

        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.encrypt.return_value = "encrypted_new_data"

            encrypted_new = await zero_knowledge_service.encrypt_user_data(
                test_db, user.id, new_data
            )

            # Should use new key for encryption
            call_args = mock_hsm.encrypt.call_args
            assert "hsm_key_67890" in str(call_args)


class TestTenantIsolation:
    """Test multi-tenant isolation and security."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_tenant_data_access_prevention(
        self, test_db, test_users_db, test_client, auth_headers
    ):
        """
        Test tenant isolation: Attempt cross-tenant data access (should fail).

        Validates that users cannot access data from other tenants.
        """
        # Create separate tenants
        tenant_a = await tenant_service.create_tenant(
            test_db,
            name="Tenant A Corp",
            domain="tenant-a.com",
            settings={"data_retention_days": 365, "encryption_required": True},
        )

        tenant_b = await tenant_service.create_tenant(
            test_db,
            name="Tenant B Inc",
            domain="tenant-b.com",
            settings={"data_retention_days": 2555, "encryption_required": True},
        )

        # Assign users to different tenants
        await tenant_service.assign_user_to_tenant(
            test_db, test_users_db["user"].id, tenant_a.id
        )
        await tenant_service.assign_user_to_tenant(
            test_db, test_users_db["manager"].id, tenant_b.id
        )

        # Create tenant-specific data
        # User from Tenant A creates a task
        response_a = test_client.post(
            "/api/v1/tasks/",
            json={
                "title": "Tenant A Task",
                "description": "Confidential task for Tenant A",
                "goal": "Process sensitive Tenant A data",
            },
            headers=auth_headers["user"],
        )
        assert response_a.status_code == 201
        task_a_id = response_a.json()["id"]

        # User from Tenant B creates a task
        response_b = test_client.post(
            "/api/v1/tasks/",
            json={
                "title": "Tenant B Task",
                "description": "Confidential task for Tenant B",
                "goal": "Process sensitive Tenant B data",
            },
            headers=auth_headers["manager"],
        )
        assert response_b.status_code == 201
        task_b_id = response_b.json()["id"]

        # Attempt cross-tenant access - User A trying to access Tenant B's task
        response = test_client.get(
            f"/api/v1/tasks/{task_b_id}", headers=auth_headers["user"]
        )
        assert response.status_code == 404  # Should appear as not found, not forbidden

        # Attempt cross-tenant access - User B trying to access Tenant A's task
        response = test_client.get(
            f"/api/v1/tasks/{task_a_id}", headers=auth_headers["manager"]
        )
        assert response.status_code == 404

        # Verify users can access their own tenant's data
        response = test_client.get(
            f"/api/v1/tasks/{task_a_id}", headers=auth_headers["user"]
        )
        assert response.status_code == 200

        response = test_client.get(
            f"/api/v1/tasks/{task_b_id}", headers=auth_headers["manager"]
        )
        assert response.status_code == 200

        # Test tenant-specific analytics isolation
        response = test_client.get(
            "/api/v1/analytics/dashboard", headers=auth_headers["user"]
        )
        assert response.status_code == 200
        tenant_a_analytics = response.json()

        response = test_client.get(
            "/api/v1/analytics/dashboard", headers=auth_headers["manager"]
        )
        assert response.status_code == 200
        tenant_b_analytics = response.json()

        # Analytics should be completely separate
        assert tenant_a_analytics != tenant_b_analytics

        # Verify task counts reflect only tenant-specific data
        assert tenant_a_analytics["task_stats"]["total_tasks"] == 1
        assert tenant_b_analytics["task_stats"]["total_tasks"] == 1

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_tenant_specific_encryption_keys(self, test_db, test_users_db):
        """
        Test tenant-specific encryption keys and data isolation.

        Validates that each tenant has separate encryption keys.
        """
        # Create tenants with different encryption requirements
        tenant_gov = await tenant_service.create_tenant(
            test_db,
            name="Government Agency",
            domain="gov.agency.com",
            settings={
                "encryption_algorithm": "AES-256-GCM",
                "key_rotation_days": 30,
                "compliance_level": "fedramp_high",
            },
        )

        tenant_corp = await tenant_service.create_tenant(
            test_db,
            name="Corporate Client",
            domain="corp.client.com",
            settings={
                "encryption_algorithm": "ChaCha20Poly1305",
                "key_rotation_days": 90,
                "compliance_level": "soc2_type2",
            },
        )

        # Generate tenant-specific master keys
        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.generate_tenant_master_key.return_value = {
                "key_id": "tenant_master_key_123",
                "algorithm": "AES-256-GCM",
            }

            gov_key = await zero_knowledge_service.generate_tenant_master_key(
                test_db, tenant_gov.id
            )

            mock_hsm.generate_tenant_master_key.return_value = {
                "key_id": "tenant_master_key_456",
                "algorithm": "ChaCha20Poly1305",
            }

            corp_key = await zero_knowledge_service.generate_tenant_master_key(
                test_db, tenant_corp.id
            )

        # Verify different keys were generated
        assert gov_key["key_id"] != corp_key["key_id"]
        assert gov_key["algorithm"] != corp_key["algorithm"]

        # Test data encryption with tenant-specific keys
        gov_data = {"classification": "top_secret", "agency": "NSA"}
        corp_data = {"classification": "confidential", "department": "HR"}

        with patch("app.core.zero_knowledge.hsm_client") as mock_hsm:
            mock_hsm.encrypt_with_tenant_key.side_effect = [
                "encrypted_gov_data_blob",
                "encrypted_corp_data_blob",
            ]

            encrypted_gov = await zero_knowledge_service.encrypt_tenant_data(
                test_db, tenant_gov.id, gov_data
            )

            encrypted_corp = await zero_knowledge_service.encrypt_tenant_data(
                test_db, tenant_corp.id, corp_data
            )

        # Verify different encryption results
        assert encrypted_gov != encrypted_corp

        # Verify correct tenant keys were used
        assert mock_hsm.encrypt_with_tenant_key.call_count == 2
        call_args_list = mock_hsm.encrypt_with_tenant_key.call_args_list

        # First call should use government tenant key
        assert "tenant_master_key_123" in str(call_args_list[0])
        # Second call should use corporate tenant key
        assert "tenant_master_key_456" in str(call_args_list[1])
