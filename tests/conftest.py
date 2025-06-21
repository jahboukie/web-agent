"""
E2E Testing Configuration for WebAgent
Comprehensive test fixtures and configuration for enterprise-grade testing
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import tempfile
from pathlib import Path

# FastAPI and database imports
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# WebAgent imports
from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_async_session
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.execution_plan import ExecutionPlan, AtomicAction
from app.models.security import EnterpriseTenant, EnterpriseRole
from app.services.user_service import UserService
from app.core.security import create_access_token

# Test configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_webagent.db"
TEST_REDIS_URL = "redis://localhost:6379/15"  # Use DB 15 for tests

# Test user data
TEST_USERS = {
    "admin": {
        "email": "admin@test.webagent.com",
        "username": "test_admin",
        "password": "TestAdmin123!",
        "full_name": "Test Administrator",
        "is_superuser": True,
        "tenant_id": "test-enterprise"
    },
    "manager": {
        "email": "manager@test.webagent.com", 
        "username": "test_manager",
        "password": "TestManager123!",
        "full_name": "Test Manager",
        "is_superuser": False,
        "tenant_id": "test-enterprise"
    },
    "user": {
        "email": "user@test.webagent.com",
        "username": "test_user", 
        "password": "TestUser123!",
        "full_name": "Test User",
        "is_superuser": False,
        "tenant_id": "test-basic"
    },
    "auditor": {
        "email": "auditor@test.webagent.com",
        "username": "test_auditor",
        "password": "TestAuditor123!",
        "full_name": "Test Auditor",
        "is_superuser": False,
        "tenant_id": "test-compliance"
    }
}

# Test website configurations for different scenarios
TEST_WEBSITES = {
    "simple_form": {
        "url": "https://httpbin.org/forms/post",
        "type": "form_submission",
        "complexity": "low",
        "expected_elements": ["input", "button", "form"]
    },
    "spa_application": {
        "url": "https://react-shopping-cart-67954.firebaseapp.com/",
        "type": "single_page_app",
        "complexity": "high", 
        "expected_elements": ["button", "div", "img"]
    },
    "authentication_required": {
        "url": "https://the-internet.herokuapp.com/login",
        "type": "authentication",
        "complexity": "medium",
        "expected_elements": ["input[type=text]", "input[type=password]", "button"]
    },
    "complex_navigation": {
        "url": "https://demo.opencart.com/",
        "type": "e_commerce",
        "complexity": "high",
        "expected_elements": ["nav", "menu", "product", "cart"]
    }
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine) -> AsyncSession:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def override_get_db(test_db):
    """Override database dependency for testing."""
    async def _override_get_db():
        yield test_db
    
    app.dependency_overrides[get_async_session] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_client(override_get_db):
    """Create test client with database override."""
    return TestClient(app)


@pytest_asyncio.fixture
async def test_users_db(test_db) -> Dict[str, User]:
    """Create test users in database."""
    users = {}
    
    for role, user_data in TEST_USERS.items():
        user = await UserService.create_user(
            test_db,
            email=user_data["email"],
            username=user_data["username"],
            password=user_data["password"],
            full_name=user_data["full_name"],
            is_superuser=user_data.get("is_superuser", False)
        )
        users[role] = user
    
    await test_db.commit()
    return users


@pytest.fixture
def auth_headers(test_users_db):
    """Generate authentication headers for different user roles."""
    headers = {}
    
    for role, user in test_users_db.items():
        token = create_access_token(data={"sub": str(user.id)})
        headers[role] = {"Authorization": f"Bearer {token}"}
    
    return headers


@pytest.fixture
def test_websites():
    """Test website configurations."""
    return TEST_WEBSITES


@pytest_asyncio.fixture
async def sample_tasks(test_db, test_users_db) -> Dict[str, Task]:
    """Create sample tasks for testing."""
    tasks = {}
    
    # Simple parsing task
    simple_task = Task(
        user_id=test_users_db["user"].id,
        title="Parse Simple Form",
        description="Parse a simple HTML form",
        goal="Extract form elements and structure",
        target_url="https://httpbin.org/forms/post",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.PENDING
    )
    test_db.add(simple_task)
    
    # Complex SPA task
    complex_task = Task(
        user_id=test_users_db["manager"].id,
        title="Parse SPA Application",
        description="Parse a complex single-page application",
        goal="Extract interactive elements and navigation",
        target_url="https://react-shopping-cart-67954.firebaseapp.com/",
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    test_db.add(complex_task)
    
    await test_db.commit()
    await test_db.refresh(simple_task)
    await test_db.refresh(complex_task)
    
    tasks["simple"] = simple_task
    tasks["complex"] = complex_task
    
    return tasks


@pytest.fixture
def test_config():
    """Test configuration settings."""
    return {
        "api_timeout": 30,
        "max_retries": 3,
        "test_data_dir": Path(__file__).parent / "data",
        "screenshot_dir": Path(__file__).parent / "screenshots",
        "reports_dir": Path(__file__).parent / "reports"
    }


@pytest.fixture(autouse=True)
def setup_test_directories(test_config):
    """Ensure test directories exist."""
    for dir_path in [test_config["test_data_dir"], test_config["screenshot_dir"], test_config["reports_dir"]]:
        dir_path.mkdir(exist_ok=True)


# Playwright fixtures for browser testing
@pytest.fixture(scope="session")
def browser_context_args():
    """Browser context configuration for Playwright."""
    return {
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "record_video_dir": "tests/videos/",
        "record_har_path": "tests/har/network.har"
    }


@pytest.fixture
def page_with_auth(page, auth_headers):
    """Playwright page with authentication headers."""
    # Set authentication headers for API requests
    page.set_extra_http_headers(auth_headers["user"])
    return page


# Security testing fixtures
@pytest.fixture
def security_test_payloads():
    """Common security test payloads."""
    return {
        "xss": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//"
        ],
        "sql_injection": [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'--"
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
    }


# Performance testing fixtures
@pytest.fixture
def load_test_config():
    """Load testing configuration."""
    return {
        "concurrent_users": 50,
        "ramp_up_time": 30,
        "test_duration": 300,  # 5 minutes
        "target_endpoints": [
            "/api/v1/web-pages/parse",
            "/api/v1/plans/generate", 
            "/api/v1/execution/run"
        ]
    }


# Chaos engineering fixtures
@pytest.fixture
def chaos_scenarios():
    """Chaos engineering test scenarios."""
    return {
        "database_failure": {
            "type": "database",
            "action": "disconnect",
            "duration": 30
        },
        "high_cpu_load": {
            "type": "resource",
            "action": "cpu_stress",
            "intensity": 90
        },
        "network_latency": {
            "type": "network",
            "action": "add_latency",
            "delay_ms": 2000
        }
    }
