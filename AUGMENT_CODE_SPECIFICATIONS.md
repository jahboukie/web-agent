# Implementation Specifications for WebAgent Development

**Document Version:** 2.0
**Date:** June 19, 2025
**Last Updated:** Phase 2A Complete
**Current Target:** Claude Code (Phase 2B Implementation)
**Previous Work:** Augment Code (Phase 2A Complete)

---

## 🎯 **CURRENT STATUS: PHASE 2A COMPLETE**

**✅ COMPLETED BY AUGMENT CODE (June 19, 2025):**
- Authentication system with JWT tokens
- Database integration with async SQLAlchemy
- User management and CRUD operations
- Security utilities and password hashing
- Application deployment and testing
- Git repository setup and initial push

**🚧 NEXT PHASE: Phase 2B - Business Logic Implementation**
**Target Developer:** Claude Code
**Focus:** Task management, web parsing, and core services

---

## Overview

This document provides detailed implementation specifications for WebAgent development. Phase 2A (Authentication & Database) has been completed by Augment Code. Phase 2B (Business Logic) is ready for implementation by Claude Code.

## Implementation Status

### ✅ Phase 1: Foundation (Claude Code - Complete)
- [x] Complete directory structure
- [x] Database schema with all models (SQLAlchemy)
- [x] Pydantic schemas for all entities
- [x] FastAPI application structure with placeholder routes
- [x] Docker development environment
- [x] CI/CD pipeline structure
- [x] Documentation framework

### ✅ Phase 2A: Authentication & Database (Augment Code - Complete)
- [x] JWT authentication system with access/refresh tokens
- [x] User registration and login endpoints working
- [x] Database connection & async session management
- [x] Alembic migrations setup and working
- [x] User CRUD operations and service layer
- [x] Security utilities (password hashing, encryption)
- [x] Structured logging with correlation IDs
- [x] Health check endpoints with database status
- [x] Application deployment and testing complete

### 🚧 Phase 2B: Business Logic (Claude Code - Ready for Implementation)
1. **Task CRUD Operations** (Priority 1)
2. **WebParser Service Implementation** (Priority 1)
3. **TaskPlanner Service Implementation** (Priority 2)
4. **ExecutionPlan Endpoints** (Priority 2)
5. **Comprehensive Testing** (Priority 3)

---

## 🎯 **CLAUDE CODE PHASE 2B TASKS**

### **IMMEDIATE PRIORITY: Replace 501 Placeholder Responses**

The following endpoints currently return `501 Not Implemented` and need business logic:

**Task Endpoints** (`app/api/v1/endpoints/tasks.py`):
- `POST /api/v1/tasks/` - Create new task
- `GET /api/v1/tasks/` - List user tasks
- `GET /api/v1/tasks/{task_id}` - Get task details
- `PUT /api/v1/tasks/{task_id}` - Update task
- `DELETE /api/v1/tasks/{task_id}` - Delete task

**WebPage Endpoints** (`app/api/v1/endpoints/web_pages.py`):
- `POST /api/v1/web-pages/parse` - Parse webpage
- `GET /api/v1/web-pages/` - List parsed pages
- `GET /api/v1/web-pages/{page_id}` - Get page details

**ExecutionPlan Endpoints** (`app/api/v1/endpoints/execution_plans.py`):
- `POST /api/v1/execution-plans/` - Create execution plan
- `GET /api/v1/execution-plans/{plan_id}` - Get plan details
- `POST /api/v1/execution-plans/{plan_id}/execute` - Execute plan

### **WORKING AUTHENTICATION PATTERN TO FOLLOW:**

Use the pattern from `app/api/v1/endpoints/auth.py` for all new endpoints:

```python
from app.api.dependencies import get_current_user, get_db
from app.models.user import User

@router.post("/tasks/")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Your implementation here
    # current_user is automatically authenticated
    # db is the database session
```

---

## ✅ Task 1: Authentication System Implementation (COMPLETE)

### Files to Implement/Modify:
- `app/core/security.py` (create)
- `app/core/auth.py` (create)
- `app/api/dependencies.py` (create)
- `app/api/v1/endpoints/auth.py` (implement business logic)
- `app/services/user_service.py` (create)

### Detailed Requirements:

#### app/core/security.py
```python
"""
Security utilities for password hashing, JWT tokens, and encryption.

Implement:
- password_hash(password: str) -> str
- verify_password(password: str, hashed: str) -> bool
- create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str
- create_refresh_token(data: dict) -> str
- verify_token(token: str) -> Optional[dict]
- encrypt_credential(data: str, key: str) -> str
- decrypt_credential(encrypted_data: str, key: str) -> str

Use:
- passlib with bcrypt for password hashing
- python-jose for JWT tokens
- cryptography.fernet for credential encryption
- Follow settings from app.core.config
"""
```

#### app/core/auth.py
```python
"""
Authentication dependency and middleware.

Implement:
- get_current_user(token: str = Depends(oauth2_scheme)) -> User
- get_current_active_user(current_user: User = Depends(get_current_user)) -> User
- require_permissions(permissions: List[str]) -> Callable
- TokenBlacklist class for logout functionality

Integration:
- Use database session dependency
- Handle JWT validation errors
- Check user active status
- Log authentication events
"""
```

#### app/services/user_service.py
```python
"""
User service with CRUD operations and authentication logic.

Implement:
- create_user(db: AsyncSession, user_data: UserCreate) -> User
- authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]
- get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]
- get_user_by_email(db: AsyncSession, email: str) -> Optional[User]
- update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> User
- update_last_login(db: AsyncSession, user_id: int) -> None

Error Handling:
- Handle duplicate email/username errors
- Validate password complexity
- Log user operations for audit
"""
```

### Implementation Notes:
- Use async/await patterns throughout
- Include comprehensive error handling
- Add structured logging with correlation IDs
- Write unit tests for all functions
- Follow security best practices (no plaintext passwords, secure token generation)

### Success Criteria:
- [ ] User registration endpoint works with validation
- [ ] Login endpoint returns valid JWT tokens
- [ ] Token refresh functionality works
- [ ] Password hashing is secure and performant
- [ ] All endpoints require proper authentication
- [ ] Unit tests achieve 90%+ coverage

---

## Task 2: Database Connection & Session Management

### Files to Implement/Modify:
- `app/db/session.py` (create)
- `app/db/init_db.py` (create)
- `app/api/dependencies.py` (add database dependency)
- `alembic/env.py` (configure)
- `alembic/versions/001_initial_migration.py` (create)

### Detailed Requirements:

#### app/db/session.py
```python
"""
Database session management with async support.

Implement:
- get_async_engine() -> AsyncEngine
- get_async_session_factory() -> async_sessionmaker
- get_db() -> AsyncGenerator[AsyncSession, None]  # FastAPI dependency
- create_tables() -> None  # For testing
- drop_tables() -> None   # For testing

Configuration:
- Use settings.ASYNC_DATABASE_URL
- Configure connection pooling
- Handle connection errors gracefully
- Add query logging in debug mode
"""
```

#### app/db/init_db.py
```python
"""
Database initialization and test data creation.

Implement:
- init_db(db: AsyncSession) -> None
- create_superuser(db: AsyncSession) -> User
- create_test_data(db: AsyncSession) -> None  # For development

Features:
- Check if tables exist
- Create initial superuser if none exists
- Add sample data for development
- Handle migration state
"""
```

#### Alembic Migration
```python
"""
Initial database migration with all models.

Include all models from:
- app.models.user
- app.models.task
- app.models.web_page
- app.models.interactive_element
- app.models.execution_plan
- app.models.security
- app.models.browser_session
- app.models.task_execution

Ensure:
- Proper foreign key constraints
- Indexes for performance
- Enum type creation
- Default values
"""
```

### Implementation Notes:
- Test database connection on application startup
- Use connection pooling for performance
- Add health check for database connectivity
- Handle database connection failures gracefully
- Create separate test database configuration

### Success Criteria:
- [ ] Database connection works with async session
- [ ] Migrations run successfully
- [ ] All models can be created and queried
- [ ] Connection pooling is configured
- [ ] Health check endpoint shows database status

---

## Task 3: Basic CRUD Operations

### Files to Implement/Modify:
- `app/services/task_service.py` (create)
- `app/api/v1/endpoints/tasks.py` (implement)
- `app/api/v1/endpoints/users.py` (implement)
- `tests/unit/test_task_service.py` (create)
- `tests/unit/test_user_service.py` (create)

### Detailed Requirements:

#### app/services/task_service.py
```python
"""
Task service with CRUD operations and business logic.

Implement:
- create_task(db: AsyncSession, user_id: int, task_data: TaskCreate) -> Task
- get_task(db: AsyncSession, task_id: int, user_id: int) -> Optional[Task]
- get_user_tasks(db: AsyncSession, user_id: int, filters: TaskFilters,
                 page: int, page_size: int) -> Tuple[List[Task], int]
- update_task(db: AsyncSession, task_id: int, user_id: int,
              task_data: TaskUpdate) -> Task
- delete_task(db: AsyncSession, task_id: int, user_id: int) -> bool
- get_task_stats(db: AsyncSession, user_id: int) -> TaskStats

Business Logic:
- Validate user owns task before operations
- Check task status before updates/deletions
- Calculate statistics efficiently
- Handle pagination properly
- Apply filters correctly
"""
```

#### Task Endpoint Implementation
Replace placeholder 501 responses with:
- Proper business logic using task_service
- Authentication using auth dependencies
- Request validation and error handling
- Structured responses with proper status codes
- Pagination support for list endpoints

#### User Endpoint Implementation
Replace placeholder 501 responses with:
- User profile management
- Preferences handling
- Authentication requirement
- Input validation

### Implementation Notes:
- Use dependency injection for database sessions
- Implement proper error handling for not found/forbidden
- Add input validation beyond Pydantic schema validation
- Include audit logging for task operations
- Optimize database queries (use select with joinedload where needed)

### Success Criteria:
- [ ] All task CRUD operations work correctly
- [ ] User can only access their own tasks
- [ ] Pagination works properly with filtering
- [ ] Error responses are consistent and informative
- [ ] Unit tests cover all service functions

---

## Task 4: WebParser Service (Basic Implementation)

### Files to Implement/Modify:
- `app/services/web_parser.py` (create)
- `app/utils/browser_manager.py` (create)
- `app/api/v1/endpoints/web_pages.py` (implement)
- `app/schemas/web_page.py` (enhance if needed)

### Detailed Requirements:

#### app/services/web_parser.py
```python
"""
Web parsing service using Playwright for DOM extraction.

Implement:
- parse_webpage(url: str, options: WebPageParseRequest) -> WebPageParseResponse
- extract_interactive_elements(page: Page) -> List[InteractiveElement]
- extract_content_blocks(page: Page) -> List[ContentBlock]
- analyze_page_structure(page: Page) -> Dict[str, Any]
- cache_webpage_data(web_page: WebPage) -> None

Features:
- Navigate to URL with proper error handling
- Wait for page load and dynamic content
- Extract all interactive elements (buttons, forms, links)
- Identify form fields and validation requirements
- Take screenshots for debugging
- Calculate accessibility and complexity scores
- Store data efficiently in database

Error Handling:
- Network timeouts
- Invalid URLs
- Page load failures
- Anti-bot detection
- JavaScript-heavy sites
"""
```

#### app/utils/browser_manager.py
```python
"""
Browser session management with Playwright.

Implement:
- get_browser_context(headless: bool = True) -> BrowserContext
- create_page(context: BrowserContext) -> Page
- configure_anti_detection(context: BrowserContext) -> None
- handle_page_errors(page: Page) -> None
- cleanup_browser_resources() -> None

Features:
- Browser pooling for performance
- Anti-detection measures (user agents, viewport sizes)
- Error handling and retries
- Screenshot capture
- Session persistence
"""
```

### Implementation Notes:
- Start with basic DOM parsing (no AI analysis yet)
- Focus on reliable element extraction
- Implement proper error handling and retries
- Add comprehensive logging
- Use async/await throughout
- Cache parsing results in Redis

### Success Criteria:
- [ ] Can parse simple web pages and extract elements
- [ ] Handles common page load scenarios
- [ ] Stores webpage data correctly in database
- [ ] Error handling works for edge cases
- [ ] Performance is acceptable (< 10 seconds for typical pages)

---

## Testing Requirements

### Unit Tests (90%+ Coverage Target)
Create comprehensive tests for:
- All service functions with mocked dependencies
- Authentication and authorization logic
- Database operations with test database
- Error handling scenarios
- Input validation edge cases

### Test Structure:
```
tests/
├── unit/
│   ├── test_user_service.py
│   ├── test_task_service.py
│   ├── test_auth.py
│   ├── test_security.py
│   └── test_web_parser.py
├── integration/
│   ├── test_api_auth.py
│   ├── test_api_tasks.py
│   └── test_database.py
└── conftest.py  # Shared fixtures
```

### Required Test Fixtures:
- Test database with rollback after each test
- Mock browser sessions for web parser tests
- Test users with different permission levels
- Sample task and webpage data

---

## Code Quality Requirements

### Code Style:
- Follow black formatting (88 character line length)
- Use isort for import organization
- Add type hints for all functions
- Include docstrings for all public methods
- Follow existing patterns in codebase

### Error Handling:
- Use specific exception types
- Include error details in responses
- Log errors with appropriate levels
- Handle async errors properly
- Provide user-friendly error messages

### Performance:
- Use async/await consistently
- Implement database query optimization
- Add caching where appropriate
- Monitor and log performance metrics
- Use connection pooling

### Security:
- Validate all inputs
- Use parameterized database queries
- Implement rate limiting
- Log security events
- Follow OWASP guidelines

---

## Completion Checklist

### ✅ Phase 2A (Core Authentication & CRUD) - COMPLETE
- [x] User registration and authentication works
- [x] JWT token management implemented
- [x] Database connections and sessions work
- [ ] Task CRUD operations functional ← **NEXT FOR CLAUDE CODE**
- [x] User profile management works
- [ ] Unit tests achieve 90%+ coverage ← **NEXT FOR CLAUDE CODE**
- [x] All endpoints require proper authentication

### 🚧 Phase 2B (Core Services) - FOR CLAUDE CODE
- [ ] Task CRUD operations replace 501 responses ← **START HERE**
- [ ] Basic web page parsing works
- [ ] Browser automation is stable
- [ ] Error handling is comprehensive
- [ ] Performance is acceptable
- [ ] Logging and monitoring implemented
- [ ] Integration tests pass
- [ ] Documentation is updated

### Handoff to Next Developer for Phase 3
After completing Phase 2B implementations, create a detailed handoff report including:
- What was implemented and tested
- Known issues or limitations
- Performance characteristics
- Areas needing architectural review
- Recommendations for Phase 3 planning

### 🔗 **CURRENT WORKING APPLICATION**
- **URL:** http://127.0.0.1:8000
- **Health Check:** http://127.0.0.1:8000/health
- **API Docs:** http://127.0.0.1:8000/docs (when debug enabled)
- **Repository:** https://github.com/jahboukie/web-agent.git
- **Test Accounts:** See CLAUDE_CODE_HANDOFF.md for credentials

---

## Development Commands

### Setup:
```bash
# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn app.main:app --reload

# Run tests
poetry run pytest -v --cov=app

# Format code
poetry run black .
poetry run isort .
```

### Docker for Supporting Services Only:
```bash
# Start supporting services (PostgreSQL, Redis, etc.)
docker-compose up -d postgres redis

# View service logs
docker-compose logs -f postgres

# Development and testing done on host machine
poetry run pytest
```

**Important:** Docker is used only for supporting services. All development, testing, and application execution is done directly on the host machine.

This specification provides a clear roadmap for implementing the core WebAgent functionality while maintaining high quality standards and following established architectural patterns.
