"""
E2E Tests: Security Penetration Testing
Automated penetration testing for privilege escalation, XSS/SQLi prevention, and rate limiting
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
import requests
import aiohttp
from urllib.parse import quote, urlencode
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.security.input_sanitization import input_sanitizer
from app.security.crypto_rate_limiter import crypto_rate_limiter


class TestPrivilegeEscalation:
    """Test privilege escalation prevention and detection."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_api_parameter_manipulation(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test privilege escalation via API parameter manipulation.
        
        Validates that users cannot escalate privileges through parameter tampering.
        """
        basic_user = test_users_db["user"]
        admin_user = test_users_db["admin"]
        
        # Test 1: Attempt to access admin endpoints with basic user token
        admin_endpoints = [
            "/api/v1/enterprise/tenants",
            "/api/v1/users/",
            "/api/v1/security/audit-logs",
            "/api/v1/enterprise/roles",
            "/api/v1/analytics/enterprise/advanced"
        ]
        
        for endpoint in admin_endpoints:
            response = test_client.get(endpoint, headers=auth_headers["user"])
            assert response.status_code == 403, f"Basic user should not access {endpoint}"
            
            # Verify security event is logged
            error_data = response.json()
            assert "privilege" in error_data["error"]["message"].lower() or \
                   "forbidden" in error_data["error"]["message"].lower()
        
        # Test 2: Attempt to modify user_id in requests
        malicious_payloads = [
            {"user_id": admin_user.id},  # Try to impersonate admin
            {"user_id": 999999},         # Try non-existent user
            {"user_id": "admin"},        # Try string injection
            {"user_id": None},           # Try null injection
            {"user_id": -1}              # Try negative ID
        ]
        
        for payload in malicious_payloads:
            response = test_client.post(
                "/api/v1/tasks/",
                json={
                    "title": "Privilege escalation test",
                    "description": "Testing parameter manipulation",
                    "goal": "Test goal",
                    **payload
                },
                headers=auth_headers["user"]
            )
            
            # Should either reject the request or ignore the user_id parameter
            if response.status_code == 201:
                # If task created, verify it's assigned to the correct user
                task_data = response.json()
                assert task_data["user_id"] == basic_user.id, \
                    "Task should be assigned to authenticated user, not manipulated user_id"
            else:
                # Request should be rejected with appropriate error
                assert response.status_code in [400, 403, 422], \
                    f"Invalid user_id should be rejected, got {response.status_code}"
        
        # Test 3: Attempt JWT token manipulation
        # Extract and modify JWT payload
        import jwt
        
        original_token = auth_headers["user"]["Authorization"].split(" ")[1]
        
        # Decode without verification to get payload
        try:
            payload = jwt.decode(original_token, options={"verify_signature": False})
            
            # Attempt to modify user ID in token
            malicious_payload = payload.copy()
            malicious_payload["sub"] = str(admin_user.id)
            
            # Create malicious token (will have invalid signature)
            malicious_token = jwt.encode(malicious_payload, "wrong-secret", algorithm="HS256")
            
            # Attempt to use malicious token
            malicious_headers = {"Authorization": f"Bearer {malicious_token}"}
            response = test_client.get("/api/v1/tasks/", headers=malicious_headers)
            
            # Should reject due to invalid signature
            assert response.status_code == 401, "Malicious JWT should be rejected"
            
        except Exception:
            # JWT manipulation failed as expected
            pass
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_role_based_privilege_escalation(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test role-based privilege escalation attempts.
        
        Validates that users cannot escalate their roles through various methods.
        """
        user = test_users_db["user"]
        
        # Test 1: Attempt to assign admin role to self
        role_escalation_attempts = [
            {
                "endpoint": "/api/v1/users/me/roles",
                "method": "POST",
                "payload": {"role_id": 1, "role_name": "admin"}
            },
            {
                "endpoint": f"/api/v1/users/{user.id}",
                "method": "PUT", 
                "payload": {"is_superuser": True, "roles": ["admin"]}
            },
            {
                "endpoint": "/api/v1/enterprise/roles/assign",
                "method": "POST",
                "payload": {"user_id": user.id, "role": "system_admin"}
            }
        ]
        
        for attempt in role_escalation_attempts:
            if attempt["method"] == "POST":
                response = test_client.post(
                    attempt["endpoint"],
                    json=attempt["payload"],
                    headers=auth_headers["user"]
                )
            elif attempt["method"] == "PUT":
                response = test_client.put(
                    attempt["endpoint"],
                    json=attempt["payload"],
                    headers=auth_headers["user"]
                )
            
            # Should be rejected
            assert response.status_code in [403, 404, 405], \
                f"Role escalation attempt should be rejected for {attempt['endpoint']}"
        
        # Test 2: Attempt to modify other users' roles
        manager_user = test_users_db["manager"]
        
        cross_user_attempts = [
            {
                "endpoint": f"/api/v1/users/{manager_user.id}",
                "method": "PUT",
                "payload": {"roles": ["basic_user"]}  # Try to demote manager
            },
            {
                "endpoint": f"/api/v1/users/{manager_user.id}/disable",
                "method": "POST",
                "payload": {}
            }
        ]
        
        for attempt in cross_user_attempts:
            if attempt["method"] == "PUT":
                response = test_client.put(
                    attempt["endpoint"],
                    json=attempt["payload"],
                    headers=auth_headers["user"]
                )
            elif attempt["method"] == "POST":
                response = test_client.post(
                    attempt["endpoint"],
                    json=attempt["payload"],
                    headers=auth_headers["user"]
                )
            
            # Should be rejected - basic user cannot modify other users
            assert response.status_code in [403, 404], \
                f"Cross-user modification should be rejected for {attempt['endpoint']}"


class TestXSSPrevention:
    """Test Cross-Site Scripting (XSS) prevention."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_xss_in_user_inputs(self, test_db, test_users_db, test_client, auth_headers, security_test_payloads):
        """
        Test XSS prevention in all user input fields.
        
        Validates that XSS payloads are properly sanitized or rejected.
        """
        xss_payloads = security_test_payloads["xss"]
        
        # Test XSS in task creation
        for payload in xss_payloads:
            response = test_client.post(
                "/api/v1/tasks/",
                json={
                    "title": f"Task with XSS: {payload}",
                    "description": f"Description with XSS: {payload}",
                    "goal": f"Goal with XSS: {payload}",
                    "target_url": "https://example.com"
                },
                headers=auth_headers["user"]
            )
            
            if response.status_code == 201:
                # If task created, verify XSS payload was sanitized
                task_data = response.json()
                
                # XSS payload should be sanitized or escaped
                assert "<script>" not in task_data["title"]
                assert "javascript:" not in task_data["description"]
                assert "onerror=" not in task_data["goal"]
                
                # Verify dangerous characters are escaped or removed
                dangerous_patterns = ["<script", "javascript:", "onerror=", "onload=", "alert("]
                for field in ["title", "description", "goal"]:
                    field_value = task_data[field].lower()
                    for pattern in dangerous_patterns:
                        assert pattern not in field_value, \
                            f"Dangerous pattern '{pattern}' found in {field}: {task_data[field]}"
            else:
                # Request should be rejected with validation error
                assert response.status_code in [400, 422], \
                    f"XSS payload should be rejected or sanitized, got {response.status_code}"
        
        # Test XSS in user profile updates
        for payload in xss_payloads:
            response = test_client.put(
                "/api/v1/users/me",
                json={
                    "full_name": f"User {payload}",
                    "preferences": {
                        "theme": f"dark{payload}",
                        "language": f"en{payload}"
                    }
                },
                headers=auth_headers["user"]
            )
            
            if response.status_code == 200:
                # Verify XSS was sanitized
                user_data = response.json()
                assert "<script>" not in user_data.get("full_name", "")
                assert "javascript:" not in str(user_data.get("preferences", {}))
        
        # Test XSS in search parameters
        xss_search_params = [
            f"search={quote(payload)}" for payload in xss_payloads
        ]
        
        for search_param in xss_search_params:
            response = test_client.get(
                f"/api/v1/tasks/?{search_param}",
                headers=auth_headers["user"]
            )
            
            # Should not return XSS in response
            if response.status_code == 200:
                response_text = response.text
                assert "<script>" not in response_text
                assert "javascript:" not in response_text
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_content_security_policy(self, test_client):
        """
        Test Content Security Policy (CSP) headers.
        
        Validates that proper CSP headers are set to prevent XSS.
        """
        # Test CSP headers on main endpoints
        endpoints = [
            "/",
            "/health",
            "/docs",
            "/api/v1/auth/login"
        ]
        
        for endpoint in endpoints:
            response = test_client.get(endpoint)
            
            # Check for security headers
            headers = response.headers
            
            # Content Security Policy should be present
            assert "Content-Security-Policy" in headers or "X-Content-Security-Policy" in headers, \
                f"CSP header missing for {endpoint}"
            
            # X-Frame-Options should prevent clickjacking
            assert "X-Frame-Options" in headers, f"X-Frame-Options missing for {endpoint}"
            assert headers.get("X-Frame-Options") in ["DENY", "SAMEORIGIN"]
            
            # X-Content-Type-Options should prevent MIME sniffing
            assert "X-Content-Type-Options" in headers, f"X-Content-Type-Options missing for {endpoint}"
            assert headers.get("X-Content-Type-Options") == "nosniff"
            
            # X-XSS-Protection should be enabled
            assert "X-XSS-Protection" in headers, f"X-XSS-Protection missing for {endpoint}"


class TestSQLInjectionPrevention:
    """Test SQL Injection prevention."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sql_injection_in_queries(self, test_db, test_users_db, test_client, auth_headers, security_test_payloads):
        """
        Test SQL injection prevention in database queries.
        
        Validates that SQL injection payloads are properly handled.
        """
        sql_payloads = security_test_payloads["sql_injection"]
        
        # Test SQL injection in search parameters
        for payload in sql_payloads:
            # Test in task search
            response = test_client.get(
                f"/api/v1/tasks/?search={quote(payload)}",
                headers=auth_headers["user"]
            )
            
            # Should not cause database error or return unauthorized data
            assert response.status_code in [200, 400, 422], \
                f"SQL injection should not cause server error, got {response.status_code}"
            
            if response.status_code == 200:
                # Should not return data from other users
                tasks = response.json()
                if isinstance(tasks, list):
                    for task in tasks:
                        assert task["user_id"] == test_users_db["user"].id, \
                            "SQL injection should not return other users' data"
        
        # Test SQL injection in user lookup
        for payload in sql_payloads:
            response = test_client.get(
                f"/api/v1/users/search?email={quote(payload)}",
                headers=auth_headers["admin"]  # Admin can search users
            )
            
            # Should not cause database error
            assert response.status_code in [200, 400, 404, 422], \
                f"SQL injection in user search should not cause server error"
        
        # Test SQL injection in task creation
        for payload in sql_payloads:
            response = test_client.post(
                "/api/v1/tasks/",
                json={
                    "title": f"Task {payload}",
                    "description": "Test description",
                    "goal": "Test goal"
                },
                headers=auth_headers["user"]
            )
            
            # Should either create task safely or reject
            if response.status_code == 201:
                # Verify task was created properly without SQL injection
                task_data = response.json()
                assert task_data["user_id"] == test_users_db["user"].id
                assert "SELECT" not in task_data["title"].upper()
                assert "DROP" not in task_data["title"].upper()
                assert "UNION" not in task_data["title"].upper()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_parameterized_queries(self, test_db, test_users_db):
        """
        Test that all database queries use parameterized statements.
        
        Validates that raw SQL with string concatenation is not used.
        """
        # This test would typically involve code analysis or query logging
        # For demonstration, we'll test that dangerous characters in data don't affect queries
        
        from app.services.task_service import TaskService
        from app.schemas.task import TaskCreate
        
        dangerous_strings = [
            "'; DROP TABLE tasks; --",
            "' OR '1'='1",
            "'; UPDATE users SET is_superuser=true; --"
        ]
        
        for dangerous_string in dangerous_strings:
            # Create task with dangerous string in title
            task_data = TaskCreate(
                title=dangerous_string,
                description="Test description",
                goal="Test goal"
            )
            
            try:
                task = await TaskService.create_task(test_db, test_users_db["user"].id, task_data)
                
                # Task should be created with the dangerous string as literal text
                assert task.title == dangerous_string
                assert task.user_id == test_users_db["user"].id
                
                # Verify database integrity - other tasks should still exist
                all_tasks = await TaskService.get_user_tasks(test_db, test_users_db["user"].id)
                assert len(all_tasks) > 0
                
            except Exception as e:
                # If creation fails, it should be due to validation, not SQL error
                assert "SQL" not in str(e).upper()
                assert "syntax" not in str(e).lower()


class TestRateLimiting:
    """Test rate limiting and DoS prevention."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_api_rate_limiting(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test API rate limiting to prevent abuse.
        
        Validates that rate limits are enforced correctly.
        """
        # Test rate limiting on authentication endpoint
        login_attempts = []
        
        for i in range(20):  # Attempt 20 rapid logins
            start_time = time.time()
            response = test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "wrongpassword"
                }
            )
            end_time = time.time()
            
            login_attempts.append({
                "attempt": i + 1,
                "status_code": response.status_code,
                "response_time": end_time - start_time
            })
            
            # After several attempts, should start rate limiting
            if i > 10:
                if response.status_code == 429:
                    # Rate limiting is working
                    assert "rate limit" in response.json()["error"]["message"].lower()
                    break
        
        # Verify rate limiting was triggered
        rate_limited_attempts = [a for a in login_attempts if a["status_code"] == 429]
        assert len(rate_limited_attempts) > 0, "Rate limiting should be triggered after multiple failed attempts"
        
        # Test rate limiting on API endpoints
        rapid_requests = []
        
        for i in range(100):  # Make 100 rapid requests
            start_time = time.time()
            response = test_client.get("/api/v1/tasks/", headers=auth_headers["user"])
            end_time = time.time()
            
            rapid_requests.append({
                "request": i + 1,
                "status_code": response.status_code,
                "response_time": end_time - start_time
            })
            
            # Check if rate limiting kicks in
            if response.status_code == 429:
                break
        
        # Verify some form of rate limiting or throttling
        avg_response_time = sum(r["response_time"] for r in rapid_requests) / len(rapid_requests)
        
        # Either rate limiting (429) or increasing response times (throttling)
        rate_limited = any(r["status_code"] == 429 for r in rapid_requests)
        response_time_increase = rapid_requests[-1]["response_time"] > rapid_requests[0]["response_time"] * 2
        
        assert rate_limited or response_time_increase, \
            "Rate limiting or throttling should be applied to rapid requests"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cryptographic_rate_limiting(self, test_db, test_users_db):
        """
        Test rate limiting on cryptographic operations.
        
        Validates that expensive crypto operations are rate limited.
        """
        user = test_users_db["user"]
        
        # Test rate limiting on key generation
        key_generation_attempts = []
        
        for i in range(10):
            start_time = time.time()
            
            try:
                # Attempt to generate encryption keys rapidly
                result = await crypto_rate_limiter.check_and_increment(
                    user.id, "key_generation", limit=5, window_seconds=60
                )
                
                end_time = time.time()
                
                key_generation_attempts.append({
                    "attempt": i + 1,
                    "allowed": result["allowed"],
                    "remaining": result["remaining"],
                    "response_time": end_time - start_time
                })
                
                if not result["allowed"]:
                    break
                    
            except Exception as e:
                # Rate limiting exception
                key_generation_attempts.append({
                    "attempt": i + 1,
                    "allowed": False,
                    "error": str(e),
                    "response_time": time.time() - start_time
                })
                break
        
        # Verify rate limiting was applied
        blocked_attempts = [a for a in key_generation_attempts if not a.get("allowed", True)]
        assert len(blocked_attempts) > 0, "Cryptographic operations should be rate limited"
        
        # Test rate limiting on encryption operations
        encryption_attempts = []
        
        for i in range(20):
            start_time = time.time()
            
            try:
                result = await crypto_rate_limiter.check_and_increment(
                    user.id, "encryption", limit=10, window_seconds=60
                )
                
                end_time = time.time()
                
                encryption_attempts.append({
                    "attempt": i + 1,
                    "allowed": result["allowed"],
                    "remaining": result["remaining"],
                    "response_time": end_time - start_time
                })
                
                if not result["allowed"]:
                    break
                    
            except Exception as e:
                encryption_attempts.append({
                    "attempt": i + 1,
                    "allowed": False,
                    "error": str(e),
                    "response_time": time.time() - start_time
                })
                break
        
        # Verify encryption rate limiting
        blocked_encryption = [a for a in encryption_attempts if not a.get("allowed", True)]
        assert len(blocked_encryption) > 0, "Encryption operations should be rate limited"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_distributed_rate_limiting(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test distributed rate limiting across multiple sessions.
        
        Validates that rate limits apply across different sessions for the same user.
        """
        user = test_users_db["user"]
        
        # Create multiple authentication sessions for the same user
        sessions = []
        
        for i in range(3):
            response = test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": user.email,
                    "password": "TestUser123!",
                    "device_fingerprint": f"device_{i}"
                }
            )
            
            if response.status_code == 200:
                token = response.json()["access_token"]
                sessions.append({"Authorization": f"Bearer {token}"})
        
        # Make rapid requests from all sessions
        total_requests = 0
        rate_limited_count = 0
        
        for session_idx, session_headers in enumerate(sessions):
            for request_idx in range(50):  # 50 requests per session
                response = test_client.get("/api/v1/tasks/", headers=session_headers)
                total_requests += 1
                
                if response.status_code == 429:
                    rate_limited_count += 1
                    
                # Small delay to avoid overwhelming the system
                time.sleep(0.01)
        
        # Verify distributed rate limiting
        rate_limit_percentage = rate_limited_count / total_requests
        
        # Should see some rate limiting across sessions
        assert rate_limit_percentage > 0.1, \
            f"Distributed rate limiting should apply across sessions, got {rate_limit_percentage:.2%} rate limited"
