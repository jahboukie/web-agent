# Background Task Processing Architecture

**Document Version:** 1.0
**Date:** June 19, 2025
**Phase:** Phase 2B - Core Intelligence Implementation
**Author:** Claude Code

---

## Executive Summary

This document defines the architecture for background task processing in WebAgent, specifically designed for long-running web parsing operations using Playwright browser automation. The system must handle concurrent parsing tasks without blocking API responses while providing robust error handling, resource management, and scalability.

## 1. Background Task System Architecture

### 1.1 Technology Decision: FastAPI BackgroundTasks + Redis Queue

**Decision:** Hybrid approach using FastAPI BackgroundTasks for MVP with Redis-based task queue for scalability

**Rationale:**
- **MVP Phase:** FastAPI BackgroundTasks for simple implementation and immediate functionality
- **Scale Phase:** Redis-based task queue system for production load and multi-worker support
- **Migration Path:** Clear upgrade path without architectural rewrites

### 1.2 Task Processing Flow

```
API Request → Task Creation → Queue → Background Worker → Result Storage → Status Update
     ↓             ↓           ↓            ↓              ↓              ↓
  Immediate     Database    Redis       Playwright      Database      Notification
  Response      Record      Queue       Processing      Update        (Optional)
```

### 1.3 Implementation Architecture

#### Phase 1: FastAPI BackgroundTasks (MVP)
```python
# Immediate implementation for Phase 2B
@app.post("/api/v1/web-pages/parse")
async def parse_webpage(
    request: WebPageParseRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Create task record immediately
    task = await create_parsing_task(db, current_user.id, request)

    # 2. Queue background processing
    background_tasks.add_task(
        process_webpage_parsing,
        task_id=task.id,
        url=request.url,
        options=request
    )

    # 3. Return immediately with task ID
    return TaskCreationResponse(
        task_id=task.id,
        status="queued",
        estimated_duration_seconds=30
    )
```

#### Phase 2: Redis Task Queue (Production Scale)
```python
# Future implementation for high-load scenarios
from app.core.task_queue import TaskQueue

@app.post("/api/v1/web-pages/parse")
async def parse_webpage(request: WebPageParseRequest, ...):
    task = await create_parsing_task(db, current_user.id, request)

    # Queue task in Redis with priority and retry config
    await TaskQueue.enqueue(
        task_type="webpage_parsing",
        task_id=task.id,
        payload=request.dict(),
        priority="normal",
        max_retries=3,
        timeout=300
    )

    return TaskCreationResponse(task_id=task.id, status="queued")
```

## 2. Task Status Tracking & Result Storage

### 2.1 Enhanced Task Model

Add background processing fields to existing Task model:

```python
# Extension to existing app/models/task.py
class Task(Base):
    # ... existing fields ...

    # Background processing fields
    background_task_id = Column(String(255), nullable=True, index=True)
    queue_name = Column(String(100), default="default")
    worker_id = Column(String(255), nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Progress tracking
    progress_details = Column(JSON, default=dict)  # {"current_step": "extracting_elements", "progress": 45}
    estimated_completion_at = Column(DateTime(timezone=True), nullable=True)

    # Resource tracking
    memory_usage_mb = Column(Integer, nullable=True)
    browser_session_id = Column(String(255), nullable=True)

    # Error handling
    retry_attempts = Column(Integer, default=0)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    error_details = Column(JSON, default=dict)
```

### 2.2 Task Status Management Service

```python
# app/services/task_status_service.py
class TaskStatusService:
    @staticmethod
    async def update_task_progress(
        db: AsyncSession,
        task_id: int,
        status: TaskStatus,
        progress_percentage: int = None,
        current_step: str = None,
        estimated_completion: datetime = None
    ):
        """Update task progress with real-time status."""

    @staticmethod
    async def mark_task_processing(
        db: AsyncSession,
        task_id: int,
        worker_id: str,
        browser_session_id: str = None
    ):
        """Mark task as actively processing."""

    @staticmethod
    async def complete_task(
        db: AsyncSession,
        task_id: int,
        result_data: dict,
        performance_metrics: dict
    ):
        """Mark task as completed with results."""

    @staticmethod
    async def fail_task(
        db: AsyncSession,
        task_id: int,
        error: Exception,
        retry_eligible: bool = True
    ):
        """Handle task failure with retry logic."""
```

### 2.3 Real-time Status Updates

```python
# WebSocket endpoint for real-time task updates
@app.websocket("/ws/tasks/{task_id}/status")
async def task_status_websocket(
    websocket: WebSocket,
    task_id: int,
    current_user: User = Depends(get_current_user)
):
    """Provide real-time task status updates via WebSocket."""
    await websocket.accept()

    # Subscribe to Redis task status updates
    async for status_update in TaskStatusService.subscribe_to_updates(task_id):
        await websocket.send_json(status_update)
```

## 3. Browser Context Management

### 3.1 Browser Pool Architecture

**Decision:** Hybrid browser management with context pooling and per-task isolation

```python
# app/utils/browser_pool.py
class BrowserPoolManager:
    def __init__(self):
        self.pool_size = settings.BROWSER_POOL_SIZE  # Default: 5
        self.active_contexts = {}
        self.available_contexts = asyncio.Queue(maxsize=self.pool_size)
        self.context_stats = {}

    async def acquire_context(self, task_id: int) -> BrowserContext:
        """Acquire a browser context for task execution."""

    async def release_context(self, task_id: int, context: BrowserContext):
        """Release browser context back to pool or cleanup."""

    async def cleanup_context(self, context: BrowserContext):
        """Clean up browser context resources."""
```

### 3.2 Session Isolation Strategy

```python
# app/models/browser_session.py enhancement
class BrowserSession(Base):
    # ... existing fields ...

    # Resource management
    context_id = Column(String(255), nullable=False, index=True)
    pool_assigned_at = Column(DateTime(timezone=True), nullable=True)
    resource_limits = Column(JSON, default=lambda: {
        "max_memory_mb": 512,
        "max_duration_seconds": 300,
        "max_pages": 10
    })

    # Anti-detection configuration
    user_agent_rotation = Column(Boolean, default=True)
    viewport_randomization = Column(Boolean, default=True)
    request_interception = Column(Boolean, default=True)
```

### 3.3 Resource Cleanup & Memory Management

```python
# app/utils/browser_cleanup.py
class BrowserCleanupService:
    @staticmethod
    async def monitor_resource_usage():
        """Monitor browser resource usage and cleanup if needed."""

    @staticmethod
    async def force_cleanup_session(session_id: str):
        """Force cleanup of browser session due to resource limits."""

    @staticmethod
    async def health_check_browsers():
        """Health check all browser contexts and restart if needed."""
```

## 4. WebParser Service Architecture

### 4.1 Service Implementation Structure

```python
# app/services/web_parser.py
class WebParserService:
    def __init__(self):
        self.browser_pool = BrowserPoolManager()
        self.cache_service = WebPageCacheService()

    async def parse_webpage_async(
        self,
        task_id: int,
        url: str,
        options: WebPageParseRequest
    ) -> WebPageParseResponse:
        """Main async parsing method for background execution."""

        # 1. Check cache first
        cached_result = await self.cache_service.get_cached_page(url, options)
        if cached_result and not options.force_refresh:
            return cached_result

        # 2. Update task status
        await TaskStatusService.update_task_progress(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            current_step="acquiring_browser"
        )

        # 3. Acquire browser context
        context = await self.browser_pool.acquire_context(task_id)

        try:
            # 4. Perform parsing
            result = await self._perform_parsing(context, url, options, task_id)

            # 5. Cache results
            await self.cache_service.cache_page_result(url, result)

            # 6. Update task completion
            await TaskStatusService.complete_task(task_id, result.dict())

            return result

        except Exception as e:
            await TaskStatusService.fail_task(task_id, e)
            raise
        finally:
            await self.browser_pool.release_context(task_id, context)

    async def _perform_parsing(
        self,
        context: BrowserContext,
        url: str,
        options: WebPageParseRequest,
        task_id: int
    ) -> WebPageParseResponse:
        """Perform the actual webpage parsing with progress updates."""

        page = await context.new_page()

        try:
            # Step 1: Navigate to page
            await TaskStatusService.update_task_progress(
                task_id=task_id,
                progress_percentage=20,
                current_step="navigating_to_page"
            )
            await page.goto(url, wait_until="networkidle")

            # Step 2: Extract DOM structure
            await TaskStatusService.update_task_progress(
                task_id=task_id,
                progress_percentage=40,
                current_step="extracting_dom"
            )
            dom_data = await self._extract_dom_structure(page)

            # Step 3: Identify interactive elements
            await TaskStatusService.update_task_progress(
                task_id=task_id,
                progress_percentage=60,
                current_step="identifying_elements"
            )
            elements = await self._extract_interactive_elements(page)

            # Step 4: Perform semantic analysis
            await TaskStatusService.update_task_progress(
                task_id=task_id,
                progress_percentage=80,
                current_step="semantic_analysis"
            )
            semantic_data = await self._perform_semantic_analysis(page, elements)

            # Step 5: Take screenshot
            await TaskStatusService.update_task_progress(
                task_id=task_id,
                progress_percentage=90,
                current_step="capturing_screenshot"
            )
            screenshot_path = await self._capture_screenshot(page, task_id)

            return WebPageParseResponse(
                web_page=WebPage(...),
                processing_time_ms=processing_time,
                screenshots=[screenshot_path],
                cache_hit=False
            )

        finally:
            await page.close()
```

### 4.2 Caching & Duplicate URL Handling

```python
# app/services/webpage_cache_service.py
class WebPageCacheService:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.cache_ttl = settings.WEBPAGE_CACHE_TTL  # 1 hour default

    async def get_cached_page(
        self,
        url: str,
        options: WebPageParseRequest
    ) -> Optional[WebPageParseResponse]:
        """Get cached webpage data if available and valid."""
        cache_key = self._generate_cache_key(url, options)
        cached_data = await self.redis_client.get(cache_key)

        if cached_data:
            # Check if cached data is still valid
            parsed_data = json.loads(cached_data)
            cached_at = datetime.fromisoformat(parsed_data['cached_at'])

            if datetime.utcnow() - cached_at < timedelta(seconds=self.cache_ttl):
                return WebPageParseResponse.parse_obj(parsed_data['result'])

        return None

    async def cache_page_result(
        self,
        url: str,
        result: WebPageParseResponse
    ):
        """Cache webpage parsing result."""
        cache_key = self._generate_cache_key(url, result.options)
        cache_data = {
            'result': result.dict(),
            'cached_at': datetime.utcnow().isoformat(),
            'url': url
        }

        await self.redis_client.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(cache_data)
        )

    def _generate_cache_key(self, url: str, options: WebPageParseRequest) -> str:
        """Generate unique cache key based on URL and parsing options."""
        option_hash = hashlib.md5(
            json.dumps(options.dict(), sort_keys=True).encode()
        ).hexdigest()
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"webpage_cache:{url_hash}:{option_hash}"
```

## 5. Error Handling & Retry Logic

### 5.1 Retry Strategy Configuration

```python
# app/core/retry_config.py
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    # Error-specific retry rules
    retry_on_errors: List[Type[Exception]] = field(default_factory=lambda: [
        aiohttp.ClientTimeout,
        playwright.async_api.TimeoutError,
        ConnectionError,
        BrowserError
    ])

    no_retry_errors: List[Type[Exception]] = field(default_factory=lambda: [
        ValidationError,
        PermissionError,
        AuthenticationError
    ])

class RetryHandler:
    @staticmethod
    async def execute_with_retry(
        func: Callable,
        config: RetryConfig,
        task_id: int,
        *args,
        **kwargs
    ):
        """Execute function with configurable retry logic."""

        for attempt in range(config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if not RetryHandler._should_retry(e, config, attempt):
                    raise

                delay = RetryHandler._calculate_delay(attempt, config)
                await TaskStatusService.update_task_progress(
                    task_id=task_id,
                    current_step=f"retrying_after_error_attempt_{attempt + 1}"
                )

                await asyncio.sleep(delay)

        raise Exception(f"Task failed after {config.max_attempts} attempts")
```

### 5.2 Error Classification & Recovery

```python
# app/utils/error_handling.py
class WebParsingErrorHandler:
    @staticmethod
    async def handle_parsing_error(
        task_id: int,
        error: Exception,
        context: dict
    ) -> ErrorRecoveryAction:
        """Classify error and determine recovery action."""

        if isinstance(error, playwright.async_api.TimeoutError):
            return ErrorRecoveryAction.RETRY_WITH_LONGER_TIMEOUT
        elif isinstance(error, BrowserCrashError):
            return ErrorRecoveryAction.RESTART_BROWSER_AND_RETRY
        elif isinstance(error, AntiDetectionError):
            return ErrorRecoveryAction.ROTATE_USER_AGENT_AND_RETRY
        elif isinstance(error, MemoryLimitExceeded):
            return ErrorRecoveryAction.CLEANUP_AND_RETRY
        else:
            return ErrorRecoveryAction.FAIL_PERMANENTLY

    @staticmethod
    async def apply_recovery_action(
        action: ErrorRecoveryAction,
        task_id: int,
        context: dict
    ):
        """Apply the determined recovery action."""
        pass
```

## 6. System Integration & Task Lifecycle

### 6.1 Task Lifecycle State Machine

```
Created → Queued → Processing → [Completed | Failed | Cancelled]
    ↓        ↓         ↓            ↓         ↓         ↓
Database  Redis    Browser     Results   Error     User
 Record   Queue    Session     Stored    Logged   Action
```

### 6.2 Integration with Future Services

```python
# app/services/task_orchestration_service.py
class TaskOrchestrationService:
    """Orchestrates the flow between WebParser, TaskPlanner, and ActionExecutor."""

    async def handle_webpage_parsed(self, task_id: int, parse_result: WebPageParseResponse):
        """Handle completion of webpage parsing and trigger next phase."""

        # 1. Store parsed webpage data
        await WebPageService.store_parsed_page(parse_result)

        # 2. Check if this should trigger task planning
        task = await TaskService.get_task_by_id(task_id)
        if task.status == TaskStatus.PENDING_PLANNING:
            await self.trigger_task_planning(task_id, parse_result.web_page.id)

    async def trigger_task_planning(self, task_id: int, web_page_id: int):
        """Trigger task planning service for a parsed webpage."""

        # Queue planning task
        await TaskQueue.enqueue(
            task_type="task_planning",
            task_id=task_id,
            payload={"web_page_id": web_page_id}
        )
```

## 7. Monitoring & Observability

### 7.1 Metrics Collection

```python
# app/utils/metrics.py
class TaskMetrics:
    @staticmethod
    async def record_task_started(task_id: int, task_type: str):
        """Record task start metrics."""

    @staticmethod
    async def record_task_completed(
        task_id: int,
        duration_seconds: float,
        memory_peak_mb: int,
        success: bool
    ):
        """Record task completion metrics."""

    @staticmethod
    async def record_browser_resource_usage(
        session_id: str,
        memory_mb: int,
        cpu_percent: float
    ):
        """Record browser resource usage."""
```

### 7.2 Health Monitoring

```python
# Enhanced health check endpoint
@app.get("/health/background-tasks")
async def background_task_health():
    """Health check for background task processing system."""

    health_status = {
        "queue_health": await TaskQueue.health_check(),
        "browser_pool_status": await BrowserPoolManager.get_pool_status(),
        "active_tasks": await TaskStatusService.get_active_task_count(),
        "failed_tasks_last_hour": await TaskStatusService.get_recent_failures(),
        "redis_connection": await redis_health_check()
    }

    return health_status
```

## 8. Implementation Specifications for Augment Code

### 8.1 Priority 1: Basic Background Task Infrastructure

**Files to Create:**
- `app/services/task_status_service.py`
- `app/utils/browser_pool.py`
- `app/services/web_parser.py` (basic version)
- `app/core/retry_config.py`

**Implementation Order:**
1. Extend Task model with background processing fields
2. Create TaskStatusService for progress tracking
3. Implement basic WebParserService with FastAPI BackgroundTasks
4. Add browser context management
5. Create error handling and retry logic

### 8.2 Priority 2: Caching & Performance

**Files to Create:**
- `app/services/webpage_cache_service.py`
- `app/utils/browser_cleanup.py`
- `app/utils/metrics.py`

### 8.3 Priority 3: Advanced Features

**Files to Create:**
- `app/core/task_queue.py` (Redis-based queue)
- `app/services/task_orchestration_service.py`
- WebSocket endpoints for real-time updates

### 8.4 Database Schema Updates

**Migration Required:**
```sql
-- Add background processing fields to tasks table
ALTER TABLE tasks ADD COLUMN background_task_id VARCHAR(255);
ALTER TABLE tasks ADD COLUMN queue_name VARCHAR(100) DEFAULT 'default';
ALTER TABLE tasks ADD COLUMN worker_id VARCHAR(255);
ALTER TABLE tasks ADD COLUMN processing_started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tasks ADD COLUMN processing_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tasks ADD COLUMN progress_details JSON DEFAULT '{}';
ALTER TABLE tasks ADD COLUMN estimated_completion_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tasks ADD COLUMN memory_usage_mb INTEGER;
ALTER TABLE tasks ADD COLUMN browser_session_id VARCHAR(255);
ALTER TABLE tasks ADD COLUMN last_error_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE tasks ADD COLUMN error_details JSON DEFAULT '{}';

-- Add indexes for performance
CREATE INDEX idx_tasks_background_task_id ON tasks(background_task_id);
CREATE INDEX idx_tasks_queue_name ON tasks(queue_name);
CREATE INDEX idx_tasks_processing_started_at ON tasks(processing_started_at);
```

## 9. Scalability Path

### 9.1 MVP → Production Migration

**Phase 1 (MVP):** FastAPI BackgroundTasks + SQLite + Local Browser Pool
**Phase 2 (Scale):** Redis Task Queue + PostgreSQL + Browser Pool + Multiple Workers
**Phase 3 (Enterprise):** Kubernetes + Cloud Browsers + Auto-scaling + Advanced Monitoring

### 9.2 Performance Targets

- **MVP:** 10 concurrent parsing tasks, 30-second average parse time
- **Scale:** 100 concurrent parsing tasks, 15-second average parse time
- **Enterprise:** 1000+ concurrent parsing tasks, sub-10-second parse time

---

This architecture provides a robust foundation for background task processing that can scale from MVP to enterprise deployment while maintaining clean separation of concerns and excellent developer experience.
