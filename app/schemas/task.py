from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator
from app.models.task import TaskStatus, TaskPriority
from app.schemas.execution_plan import ExecutionPlan


class TaskBase(BaseModel):
    title: str = Field(max_length=255)
    description: str
    goal: str
    target_url: Optional[HttpUrl] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    require_confirmation: bool = False
    allow_sensitive_actions: bool = False


class TaskCreate(TaskBase):
    user_id: Optional[int] = None  # Will be set from authentication


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    current_step: Optional[int] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    require_confirmation: Optional[bool] = None
    allow_sensitive_actions: Optional[bool] = None


class Task(TaskBase):
    id: int
    user_id: int
    status: TaskStatus = TaskStatus.PENDING
    progress_percentage: int = 0
    execution_plan_id: Optional[int] = None
    current_step: int = 0
    total_steps: int = 0
    result_data: Dict[str, Any] = {}
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_seconds: Optional[int] = None
    actual_duration_seconds: Optional[int] = None
    retry_count: int = 0
    
    # Optional relationships
    execution_plan: Optional[ExecutionPlan] = None

    class Config:
        from_attributes = True

    @validator('progress_percentage')
    def validate_progress(cls, v, values):
        if v < 0 or v > 100:
            raise ValueError('Progress percentage must be between 0 and 100')
        return v


class TaskExecutionRequest(BaseModel):
    task_id: int
    force_restart: bool = False
    skip_validation: bool = False
    debug_mode: bool = False
    screenshot_frequency: int = Field(default=5, ge=1, le=50)  # Screenshots every N actions


class TaskExecutionResponse(BaseModel):
    task_id: int
    execution_id: str
    status: str
    message: str
    estimated_duration_seconds: Optional[int] = None


class TaskStatusUpdate(BaseModel):
    task_id: int
    status: TaskStatus
    progress_percentage: int = Field(ge=0, le=100)
    current_step: int
    current_action_description: Optional[str] = None
    screenshots: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskResult(BaseModel):
    task_id: int
    success: bool
    result_data: Dict[str, Any] = {}
    extracted_data: Dict[str, Any] = {}
    execution_duration_seconds: int
    actions_executed: int
    pages_visited: int
    screenshots: List[str] = []
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = {}
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    completion_timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskList(BaseModel):
    tasks: List[Task]
    total_count: int
    page: int = 1
    page_size: int = 20
    has_next: bool = False
    has_previous: bool = False


class TaskFilters(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    domain: Optional[str] = None
    search_query: Optional[str] = Field(None, max_length=200)


class TaskStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    pending_tasks: int
    success_rate: float = Field(ge=0.0, le=1.0)
    average_duration_seconds: Optional[float] = None
    most_common_domains: List[Dict[str, Any]] = []
    recent_activity: List[Dict[str, Any]] = []