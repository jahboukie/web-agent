# WebAgent Coding Standards

**Version:** 1.0
**Date:** June 19, 2025
**Scope:** All Python code in the WebAgent project

---

## Code Formatting & Style

### Python Code Formatting
- **Tool:** Black with 88-character line length
- **Import Organization:** isort with black profile
- **Configuration:** Defined in `pyproject.toml`

```bash
# Format code
poetry run black .
poetry run isort .

# Check formatting
poetry run black --check .
poetry run isort --check-only .
```

### Line Length & Structure
- **Maximum line length:** 88 characters (Black default)
- **Indentation:** 4 spaces (no tabs)
- **Blank lines:** 2 blank lines between top-level classes/functions
- **Trailing commas:** Required for multi-line constructs

### Import Organization
```python
# Standard library imports
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, Integer, String
from pydantic import BaseModel, Field

# Local application imports
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate
```

## Type Hints & Documentation

### Type Annotations
**Required for all:**
- Function parameters
- Function return types
- Class attributes
- Module-level variables

```python
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

def create_user(
    db: AsyncSession,
    user_data: UserCreate,
    permissions: Optional[List[str]] = None
) -> User:
    """Create a new user with optional permissions."""
    pass

# Class with typed attributes
class UserService:
    db: AsyncSession
    cache_ttl: int = 3600

    def __init__(self, db: AsyncSession):
        self.db = db
```

### Docstring Standards
**Format:** Google style docstrings

```python
def parse_webpage(url: str, options: WebPageParseRequest) -> WebPageParseResponse:
    """Parse a webpage and extract semantic information.

    Analyzes the webpage structure, extracts interactive elements,
    and performs semantic analysis for automation planning.

    Args:
        url: The webpage URL to parse
        options: Parsing configuration and options

    Returns:
        WebPageParseResponse containing parsed data and metadata

    Raises:
        ValidationError: If URL is invalid or inaccessible
        BrowserError: If browser automation fails

    Example:
        >>> options = WebPageParseRequest(url="https://example.com")
        >>> result = await parse_webpage("https://example.com", options)
        >>> print(f"Found {len(result.web_page.interactive_elements)} elements")
    """
    pass
```

## Code Organization

### File & Directory Structure
```
app/
├── core/           # Core functionality (config, security, auth)
├── api/            # API routes and dependencies
│   ├── v1/         # API version 1
│   └── middleware/ # Custom middleware
├── models/         # SQLAlchemy database models
├── schemas/        # Pydantic request/response models
├── services/       # Business logic layer
├── utils/          # Utility functions and helpers
├── executors/      # Task execution logic
└── tools/          # Custom tools and integrations
```

### Module Organization
- **One class per file** for models and services
- **Related functions grouped** in utility modules
- **Clear separation** between layers (API, service, data)

### Naming Conventions
```python
# Variables and functions: snake_case
user_id = 123
def get_current_user(): pass

# Classes: PascalCase
class TaskService: pass
class WebPageParser: pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30

# Private attributes: leading underscore
class BrowserManager:
    def __init__(self):
        self._browser_pool = []
        self._session_count = 0
```

## Database & ORM Patterns

### SQLAlchemy Model Standards
```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    # Primary key first
    id = Column(Integer, primary_key=True, index=True)

    # Required fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)

    # Optional fields
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps at the end
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships at the end
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
```

### Database Service Patterns
```python
class UserService:
    @staticmethod
    async def create(db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user."""
        db_user = User(**user_data.dict())
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
```

## API Development Standards

### FastAPI Route Organization
```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

router = APIRouter()

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Task:
    """Create a new automation task."""
    try:
        task = await TaskService.create(db, current_user.id, task_data)
        return task
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
```

### Error Handling Patterns
```python
# Custom exceptions
class WebAgentException(Exception):
    """Base exception for WebAgent application."""
    pass

class TaskNotFoundError(WebAgentException):
    """Task not found or access denied."""
    pass

class BrowserError(WebAgentException):
    """Browser automation error."""
    pass

# Error handling in endpoints
@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await TaskService.get_by_id(db, task_id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task
```

## Async Programming Standards

### Async/Await Usage
```python
# Always use async/await for I/O operations
async def fetch_webpage(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

# Use asyncio.gather for concurrent operations
async def process_multiple_pages(urls: List[str]) -> List[WebPage]:
    tasks = [parse_webpage(url) for url in urls]
    return await asyncio.gather(*tasks)

# Proper async context managers
async def with_browser_session() -> AsyncGenerator[BrowserSession, None]:
    session = await create_browser_session()
    try:
        yield session
    finally:
        await session.close()
```

### Database Async Patterns
```python
# Use async sessions consistently
async def get_user_tasks(db: AsyncSession, user_id: int) -> List[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.user_id == user_id)
        .options(joinedload(Task.execution_plan))
    )
    return result.scalars().all()

# Proper transaction handling
async def create_task_with_plan(
    db: AsyncSession,
    task_data: TaskCreate,
    plan_data: ExecutionPlanCreate
) -> Task:
    async with db.begin():
        task = Task(**task_data.dict())
        db.add(task)
        await db.flush()  # Get task.id

        plan = ExecutionPlan(task_id=task.id, **plan_data.dict())
        db.add(plan)

        return task
```

## Testing Standards

### Test Organization
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.user_service import UserService
from app.schemas.user import UserCreate

class TestUserService:
    """Test suite for UserService."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session, sample_user_data):
        """Test successful user creation."""
        # Arrange
        user_data = UserCreate(**sample_user_data)

        # Act
        user = await UserService.create(db_session, user_data)

        # Assert
        assert user.email == sample_user_data["email"]
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, db_session, existing_user):
        """Test user creation with duplicate email."""
        # Arrange
        user_data = UserCreate(email=existing_user.email, username="different")

        # Act & Assert
        with pytest.raises(IntegrityError):
            await UserService.create(db_session, user_data)
```

### Test Fixtures
```python
# conftest.py
@pytest.fixture
async def db_session():
    """Create test database session."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePassword123!",
        "full_name": "Test User"
    }
```

## Logging Standards

### Structured Logging
```python
import structlog

logger = structlog.get_logger(__name__)

async def create_task(user_id: int, task_data: TaskCreate) -> Task:
    """Create a new task with proper logging."""
    logger.info(
        "Creating new task",
        user_id=user_id,
        task_type=task_data.task_type,
        target_url=task_data.target_url
    )

    try:
        task = await TaskService.create(db, user_id, task_data)
        logger.info(
            "Task created successfully",
            task_id=task.id,
            user_id=user_id,
            execution_time_ms=processing_time
        )
        return task
    except Exception as e:
        logger.error(
            "Failed to create task",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

### Log Levels
- **DEBUG:** Detailed information for debugging
- **INFO:** General information about application flow
- **WARNING:** Something unexpected but not an error
- **ERROR:** Error occurred but application can continue
- **CRITICAL:** Serious error, application may not continue

## Security Standards

### Input Validation
```python
from pydantic import BaseModel, validator, Field

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    goal: str = Field(min_length=10, max_length=1000)
    target_url: Optional[HttpUrl] = None

    @validator('goal')
    def validate_goal(cls, v):
        # Remove potentially dangerous content
        cleaned = bleach.clean(v, tags=[], strip=True)
        if len(cleaned) < 10:
            raise ValueError('Goal must be at least 10 characters')
        return cleaned
```

### Credential Handling
```python
# Never log sensitive data
logger.info("User authenticated", user_id=user.id)  # Good
logger.info("Password check", password=password)    # BAD

# Use environment variables for secrets
from app.core.config import settings
api_key = settings.OPENAI_API_KEY  # Good
api_key = "sk-1234567890abcdef"    # BAD

# Encrypt sensitive data
from app.core.security import encrypt_credential
encrypted = encrypt_credential(password, encryption_key)
```

## Performance Standards

### Database Query Optimization
```python
# Use select with specific columns
users = await db.execute(
    select(User.id, User.email, User.username)
    .where(User.is_active == True)
)

# Use joinedload for related data
tasks = await db.execute(
    select(Task)
    .options(joinedload(Task.execution_plan))
    .where(Task.user_id == user_id)
)

# Use pagination for large datasets
def paginate_query(query, page: int, page_size: int):
    offset = (page - 1) * page_size
    return query.offset(offset).limit(page_size)
```

### Caching Patterns
```python
from functools import lru_cache
import redis

@lru_cache(maxsize=100)
def get_config_value(key: str) -> str:
    """Cache configuration values."""
    return settings.get(key)

async def get_cached_webpage(url: str) -> Optional[WebPage]:
    """Get webpage from cache."""
    cache_key = f"webpage:{hashlib.md5(url.encode()).hexdigest()}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return WebPage.parse_raw(cached_data)
    return None
```

## Code Review Checklist

### Before Submitting Code
- [ ] Code follows formatting standards (black, isort)
- [ ] All functions have type hints and docstrings
- [ ] Unit tests written with 90%+ coverage
- [ ] No hardcoded secrets or credentials
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate and structured
- [ ] Performance implications considered
- [ ] Security best practices followed

### Review Criteria
- [ ] Code is readable and maintainable
- [ ] Architecture follows established patterns
- [ ] Database queries are optimized
- [ ] Async patterns used correctly
- [ ] Tests cover edge cases
- [ ] Documentation is updated
- [ ] No breaking changes without discussion

---

These standards ensure consistent, maintainable, and high-quality code across the WebAgent project. All team members and AI assistants should follow these guidelines when contributing to the codebase.
