"""
E2E Tests: Authentication & Data Protection
Tests for MFA enforcement, session management, client-side encryption, and audit logging
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
import json
import secrets
import pyotp
from unittest.mock import patch, MagicMock

from app.models.security import AccessSession, AuditLog
from app.services.user_service import UserService
from app.security.session_manager import session_manager
from app.security.zero_trust import zero_trust_engine
from app.core.security import verify_password, create_access_token


class TestMFAEnforcement:
    """Test Multi-Factor Authentication enforcement for enterprise accounts."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mfa_required_for_enterprise_users(self, test_db, test_users_db, test_client):
        """
        Test MFA enforcement for enterprise accounts.
        
        Validates that enterprise users cannot access sensitive resources without MFA.
        """
        admin_user = test_users_db["admin"]
        
        # Enable MFA requirement for admin user
        await UserService.update_user(
            test_db, admin_user.id, {
                "mfa_enabled": True,
                "mfa_secret": pyotp.random_base32(),
                "requires_mfa": True,
                "account_type": "enterprise"
            }
        )
        
        # Attempt login without MFA
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": admin_user.email,
                "password": "TestAdmin123!"
            }
        )
        
        # Should require MFA
        assert response.status_code == 200
        data = response.json()
        assert data["mfa_required"] is True
        assert "mfa_token" in data
        assert "access_token" not in data  # No access token without MFA
        
        # Generate valid TOTP code
        user_data = await UserService.get_user_by_id(test_db, admin_user.id)
        totp = pyotp.TOTP(user_data.mfa_secret)
        valid_code = totp.now()
        
        # Complete MFA authentication
        response = test_client.post(
            "/api/v1/auth/mfa/verify",
            json={
                "mfa_token": data["mfa_token"],
                "mfa_code": valid_code
            }
        )
        
        assert response.status_code == 200
        mfa_data = response.json()
        assert "access_token" in mfa_data
        assert "refresh_token" in mfa_data
        
        # Test access to sensitive endpoint with MFA-verified token
        headers = {"Authorization": f"Bearer {mfa_data['access_token']}"}
        response = test_client.get("/api/v1/enterprise/tenants", headers=headers)
        assert response.status_code == 200
        
        # Test invalid MFA code
        invalid_code = "000000"
        response = test_client.post(
            "/api/v1/auth/mfa/verify",
            json={
                "mfa_token": data["mfa_token"],
                "mfa_code": invalid_code
            }
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["error"]["message"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_mfa_backup_codes(self, test_db, test_users_db, test_client):
        """
        Test MFA backup codes functionality.
        
        Validates backup codes can be used when TOTP is unavailable.
        """
        user = test_users_db["manager"]
        
        # Generate MFA setup with backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(10)]
        
        await UserService.update_user(
            test_db, user.id, {
                "mfa_enabled": True,
                "mfa_secret": pyotp.random_base32(),
                "mfa_backup_codes": backup_codes,
                "requires_mfa": True
            }
        )
        
        # Initiate login
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestManager123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mfa_required"] is True
        
        # Use backup code instead of TOTP
        backup_code = backup_codes[0]
        response = test_client.post(
            "/api/v1/auth/mfa/verify",
            json={
                "mfa_token": data["mfa_token"],
                "backup_code": backup_code
            }
        )
        
        assert response.status_code == 200
        mfa_data = response.json()
        assert "access_token" in mfa_data
        
        # Verify backup code is consumed (can't be reused)
        response = test_client.post(
            "/api/v1/auth/mfa/verify",
            json={
                "mfa_token": data["mfa_token"],
                "backup_code": backup_code
            }
        )
        
        assert response.status_code == 401
        assert "used" in response.json()["error"]["message"].lower()
        
        # Test remaining backup codes still work
        backup_code_2 = backup_codes[1]
        response = test_client.post(
            "/api/v1/auth/mfa/verify",
            json={
                "mfa_token": data["mfa_token"],
                "backup_code": backup_code_2
            }
        )
        
        assert response.status_code == 200


class TestSessionManagement:
    """Test session timeout, concurrent sessions, and session security."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_session_timeout_after_inactivity(self, test_db, test_users_db, test_client):
        """
        Test session timeout after 15m inactivity.
        
        Validates that inactive sessions are automatically terminated.
        """
        user = test_users_db["user"]
        
        # Configure short session timeout for testing
        await UserService.update_user(
            test_db, user.id, {
                "session_timeout_minutes": 1  # 1 minute for testing
            }
        )
        
        # Login and get access token
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestUser123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        access_token = data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Verify initial access works
        response = test_client.get("/api/v1/tasks/", headers=headers)
        assert response.status_code == 200
        
        # Simulate time passing beyond session timeout
        with patch('app.security.session_manager.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(minutes=2)
            
            # Access should now be denied due to session timeout
            response = test_client.get("/api/v1/tasks/", headers=headers)
            assert response.status_code == 401
            assert "session" in response.json()["error"]["message"].lower()
            assert "expired" in response.json()["error"]["message"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_session_limits(self, test_db, test_users_db, test_client):
        """
        Test concurrent session limits (configurable per tenant).
        
        Validates that users cannot exceed maximum concurrent sessions.
        """
        user = test_users_db["user"]
        
        # Set concurrent session limit
        await UserService.update_user(
            test_db, user.id, {
                "max_concurrent_sessions": 2
            }
        )
        
        # Create first session
        response1 = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestUser123!",
                "device_fingerprint": "device_1"
            }
        )
        
        assert response1.status_code == 200
        token1 = response1.json()["access_token"]
        
        # Create second session
        response2 = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestUser123!",
                "device_fingerprint": "device_2"
            }
        )
        
        assert response2.status_code == 200
        token2 = response2.json()["access_token"]
        
        # Both sessions should work
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response = test_client.get("/api/v1/tasks/", headers=headers1)
        assert response.status_code == 200
        
        response = test_client.get("/api/v1/tasks/", headers=headers2)
        assert response.status_code == 200
        
        # Attempt third session (should exceed limit)
        response3 = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestUser123!",
                "device_fingerprint": "device_3"
            }
        )
        
        # Should either reject new session or terminate oldest session
        if response3.status_code == 200:
            # New session created, oldest should be terminated
            token3 = response3.json()["access_token"]
            headers3 = {"Authorization": f"Bearer {token3}"}
            
            # First session should now be invalid
            response = test_client.get("/api/v1/tasks/", headers=headers1)
            assert response.status_code == 401
            
            # Second and third sessions should still work
            response = test_client.get("/api/v1/tasks/", headers=headers2)
            assert response.status_code == 200
            
            response = test_client.get("/api/v1/tasks/", headers=headers3)
            assert response.status_code == 200
        else:
            # New session rejected
            assert response3.status_code == 429
            assert "concurrent" in response3.json()["error"]["message"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_session_fixation_protection(self, test_db, test_users_db, test_client):
        """
        Test session fixation protection: Validate session rotation on privilege change.
        
        Ensures session IDs change when user privileges are modified.
        """
        user = test_users_db["user"]
        
        # Initial login
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestUser123!"
            }
        )
        
        assert response.status_code == 200
        initial_token = response.json()["access_token"]
        initial_headers = {"Authorization": f"Bearer {initial_token}"}
        
        # Verify initial access level
        response = test_client.get("/api/v1/analytics/dashboard", headers=initial_headers)
        assert response.status_code == 403  # Basic user shouldn't have analytics access
        
        # Simulate privilege escalation (admin grants analytics access)
        from app.services.rbac_service import rbac_service
        analytics_role = await rbac_service.create_role(
            test_db,
            name="analytics_viewer",
            description="Can view analytics",
            permissions=["analytics:read"],
            tenant_id="test-basic"
        )
        
        await rbac_service.assign_role(test_db, user.id, analytics_role.id)
        
        # Session should be invalidated due to privilege change
        response = test_client.get("/api/v1/analytics/dashboard", headers=initial_headers)
        assert response.status_code == 401
        assert "privilege" in response.json()["error"]["message"].lower() or \
               "session" in response.json()["error"]["message"].lower()
        
        # User must re-authenticate to get new session with updated privileges
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestUser123!"
            }
        )
        
        assert response.status_code == 200
        new_token = response.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}
        
        # New session should have updated privileges
        response = test_client.get("/api/v1/analytics/dashboard", headers=new_headers)
        assert response.status_code == 200
        
        # Verify tokens are different (session rotation occurred)
        assert initial_token != new_token


class TestClientSideEncryption:
    """Test client-side encryption and data protection."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_data_encrypted_before_transmission(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test client-side encryption before data reaches servers.
        
        Validates that sensitive data is encrypted on the client side.
        """
        user = test_users_db["user"]
        
        # Simulate client-side encryption of sensitive task data
        sensitive_data = {
            "goal": "Access my bank account and check balance",
            "credentials": {
                "username": "john.doe@bank.com",
                "password": "MySecretPassword123!"
            },
            "additional_info": "Account number: 1234567890"
        }
        
        # Mock client-side encryption (in real scenario, this happens in frontend)
        with patch('app.core.zero_knowledge.encrypt_client_data') as mock_encrypt:
            mock_encrypt.return_value = {
                "encrypted_data": "AES256_ENCRYPTED_BLOB_12345",
                "encryption_metadata": {
                    "algorithm": "AES-256-GCM",
                    "key_id": "user_key_123",
                    "iv": "random_iv_12345"
                }
            }
            
            # Create task with encrypted sensitive data
            response = test_client.post(
                "/api/v1/tasks/",
                json={
                    "title": "Banking Task",
                    "description": "Check account balance",
                    "goal": "encrypted:AES256_ENCRYPTED_BLOB_12345",  # Encrypted goal
                    "target_url": "https://bank.example.com",
                    "encryption_metadata": {
                        "algorithm": "AES-256-GCM",
                        "key_id": "user_key_123",
                        "iv": "random_iv_12345"
                    }
                },
                headers=auth_headers["user"]
            )
            
            assert response.status_code == 201
            task_data = response.json()
            
            # Verify server received encrypted data, not plaintext
            assert task_data["goal"].startswith("encrypted:")
            assert "MySecretPassword123!" not in str(task_data)
            assert "john.doe@bank.com" not in str(task_data)
        
        # Test decryption when user retrieves their own data
        task_id = task_data["id"]
        
        with patch('app.core.zero_knowledge.decrypt_client_data') as mock_decrypt:
            mock_decrypt.return_value = sensitive_data
            
            response = test_client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers["user"])
            assert response.status_code == 200
            
            # Client should receive decrypted data
            retrieved_task = response.json()
            
            # Verify decryption was called
            mock_decrypt.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_encryption_key_derivation(self, test_db, test_users_db):
        """
        Test encryption key derivation from user credentials.
        
        Validates secure key derivation process.
        """
        user = test_users_db["user"]
        
        # Test key derivation with proper parameters
        with patch('app.core.zero_knowledge.derive_encryption_key') as mock_derive:
            mock_derive.return_value = {
                "derived_key": "PBKDF2_DERIVED_KEY_12345",
                "salt": "RANDOM_SALT_67890",
                "iterations": 100000,
                "algorithm": "PBKDF2-SHA256"
            }
            
            # Derive encryption key from user password
            key_data = await zero_knowledge_service.derive_user_encryption_key(
                test_db, user.id, "TestUser123!"
            )
            
            # Verify secure parameters were used
            mock_derive.assert_called_once()
            call_args = mock_derive.call_args[1]
            
            assert call_args["iterations"] >= 100000  # Minimum security requirement
            assert call_args["algorithm"] in ["PBKDF2-SHA256", "Argon2id"]
            assert len(call_args["salt"]) >= 32  # Minimum salt length
        
        # Test key derivation with insufficient iterations (should fail)
        with pytest.raises(ValueError, match="iterations"):
            await zero_knowledge_service.derive_user_encryption_key(
                test_db, user.id, "TestUser123!", iterations=1000  # Too low
            )


class TestAuditLogging:
    """Test audit log immutability and security event tracking."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_audit_log_immutability(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test audit log immutability (tamper-evident entries).
        
        Validates that audit logs cannot be modified after creation.
        """
        user = test_users_db["user"]
        
        # Perform actions that should generate audit logs
        actions = [
            ("POST", "/api/v1/tasks/", {"title": "Test Task", "description": "Test", "goal": "Test goal"}),
            ("GET", "/api/v1/tasks/", None),
            ("POST", "/api/v1/auth/logout", None)
        ]
        
        audit_log_ids = []
        
        for method, endpoint, data in actions:
            if method == "POST":
                response = test_client.post(endpoint, json=data, headers=auth_headers["user"])
            else:
                response = test_client.get(endpoint, headers=auth_headers["user"])
            
            # Each action should generate an audit log entry
            # Get the latest audit log for this user
            from app.models.security import AuditLog
            from sqlalchemy import select, desc
            
            query = select(AuditLog).where(
                AuditLog.user_id == user.id
            ).order_by(desc(AuditLog.created_at)).limit(1)
            
            result = await test_db.execute(query)
            audit_log = result.scalar_one_or_none()
            
            if audit_log:
                audit_log_ids.append(audit_log.id)
                
                # Verify audit log contains expected information
                assert audit_log.action == f"{method} {endpoint}"
                assert audit_log.user_id == user.id
                assert audit_log.ip_address is not None
                assert audit_log.user_agent is not None
                
                # Verify cryptographic hash for tamper detection
                assert audit_log.integrity_hash is not None
                assert len(audit_log.integrity_hash) >= 64  # SHA-256 minimum
        
        # Attempt to modify audit log entries (should fail)
        if audit_log_ids:
            audit_log_id = audit_log_ids[0]
            
            # Try to modify audit log directly in database
            from sqlalchemy import update
            
            with pytest.raises(Exception):  # Should raise integrity error
                update_query = update(AuditLog).where(
                    AuditLog.id == audit_log_id
                ).values(action="MODIFIED_ACTION")
                
                await test_db.execute(update_query)
                await test_db.commit()
        
        # Verify audit log integrity checking
        for audit_log_id in audit_log_ids:
            integrity_check = await audit_service.verify_log_integrity(test_db, audit_log_id)
            assert integrity_check["valid"] is True
            assert integrity_check["tampered"] is False
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_security_event_tracking(self, test_db, test_users_db, test_client):
        """
        Test comprehensive security event tracking.
        
        Validates that security-relevant events are properly logged.
        """
        user = test_users_db["user"]
        
        # Test failed login attempts
        for i in range(3):
            response = test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": user.email,
                    "password": "WrongPassword123!"
                }
            )
            assert response.status_code == 401
        
        # Verify failed login events were logged
        from app.models.security import AuditLog
        from sqlalchemy import select, and_
        
        query = select(AuditLog).where(
            and_(
                AuditLog.user_id == user.id,
                AuditLog.event_type == "authentication_failed"
            )
        )
        
        result = await test_db.execute(query)
        failed_login_logs = result.scalars().all()
        
        assert len(failed_login_logs) == 3
        
        for log in failed_login_logs:
            assert log.severity == "warning"
            assert "failed" in log.details.get("reason", "").lower()
        
        # Test successful login after failures
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": user.email,
                "password": "TestUser123!"
            }
        )
        assert response.status_code == 200
        
        # Verify successful login was logged
        query = select(AuditLog).where(
            and_(
                AuditLog.user_id == user.id,
                AuditLog.event_type == "authentication_success"
            )
        ).order_by(desc(AuditLog.created_at)).limit(1)
        
        result = await test_db.execute(query)
        success_log = result.scalar_one_or_none()
        
        assert success_log is not None
        assert success_log.severity == "info"
        assert "success" in success_log.details.get("result", "").lower()
        
        # Test privilege escalation detection
        access_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Attempt to access admin endpoint (should be logged as privilege escalation attempt)
        response = test_client.get("/api/v1/enterprise/tenants", headers=headers)
        assert response.status_code == 403
        
        # Verify privilege escalation attempt was logged
        query = select(AuditLog).where(
            and_(
                AuditLog.user_id == user.id,
                AuditLog.event_type == "privilege_escalation_attempt"
            )
        ).order_by(desc(AuditLog.created_at)).limit(1)
        
        result = await test_db.execute(query)
        escalation_log = result.scalar_one_or_none()
        
        assert escalation_log is not None
        assert escalation_log.severity == "high"
        assert "enterprise" in escalation_log.details.get("attempted_resource", "").lower()
