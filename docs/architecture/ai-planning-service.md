# WebAgent Phase 2C: AI Planning Service Architecture

**Status:** Design Phase - Architecture Specification  
**Date:** June 19, 2025  
**Phase:** 2C - AI Brain (Planning Service)  
**Objective:** Give WebAgent intelligent reasoning capabilities to convert user goals into executable action plans

---

## 🧠 **Phase 2C Mission: The AI Brain**

Building on Phase 2B's semantic understanding capabilities, Phase 2C introduces intelligent planning - the ability to analyze parsed webpage data and user goals to generate structured, executable action plans.

**Core Concept:** Transform WebAgent from "understanding websites" to "reasoning about web tasks"

---

## 🎯 **Architecture Overview**

### **Planning Service Flow**
```
User Goal + Parsed Webpage Data → LangChain ReAct Agent → Structured ExecutionPlan → Human Approval → Ready for Execution
```

### **Key Components**
1. **LangChain Planning Service** - ReAct agent with custom tools for web reasoning
2. **ExecutionPlan Database Models** - Structured storage for generated plans
3. **Planning API Endpoints** - Background task integration for plan generation
4. **Confidence & Validation System** - Quality assessment and human oversight
5. **Agent Memory & Learning** - Improvement from successful/failed executions

---

## 🔧 **1. LangChain Planning Service Architecture**

### **ReAct Agent Configuration**
```python
# Core Agent Setup
agent = create_react_agent(
    llm=ChatAnthropic(model="claude-3-5-sonnet-20241022"),
    tools=[
        WebpageAnalysisTool,
        ElementInspectorTool, 
        ActionCapabilityAssessor,
        PlanValidatorTool,
        ConfidenceCalculator
    ],
    prompt=WEBAGENT_PLANNING_PROMPT
)

# Agent Execution with Memory
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=ConversationBufferWindowMemory(k=10),
    max_iterations=15,
    early_stopping_method="generate"
)
```

### **Custom LangChain Tools**

#### **WebpageAnalysisTool**
```python
class WebpageAnalysisTool(BaseTool):
    """Analyzes parsed webpage data to understand structure and capabilities."""
    
    name = "webpage_analyzer"
    description = "Analyze semantic webpage data to understand page structure, interactive elements, and automation possibilities"
    
    def _run(self, webpage_data: Dict) -> Dict:
        # Analyze interactive elements
        # Assess action capabilities
        # Identify navigation patterns
        # Calculate automation feasibility
```

#### **ElementInspectorTool**
```python
class ElementInspectorTool(BaseTool):
    """Deep inspection of specific webpage elements for action planning."""
    
    name = "element_inspector"
    description = "Inspect specific webpage elements to determine interaction methods and confidence levels"
    
    def _run(self, element_selector: str, webpage_data: Dict) -> Dict:
        # Extract element properties
        # Assess interaction confidence
        # Identify required actions
        # Validate element accessibility
```

#### **ActionCapabilityAssessor**
```python
class ActionCapabilityAssessor(BaseTool):
    """Assesses what actions are possible on the current webpage."""
    
    name = "action_assessor"
    description = "Determine what actions (CLICK, TYPE, NAVIGATE, etc.) are possible given the current webpage state"
    
    def _run(self, goal: str, webpage_data: Dict) -> Dict:
        # Map user goal to actionable steps
        # Assess feasibility of each step
        # Identify potential obstacles
        # Generate confidence scores
```

### **System Prompt Engineering**
```python
WEBAGENT_PLANNING_PROMPT = PromptTemplate.from_template("""
You are WebAgent's AI Planning Service - an expert at analyzing websites and creating executable automation plans.

CONTEXT:
- User Goal: {user_goal}
- Current Webpage: {webpage_url}
- Parsed Data Available: {webpage_summary}

CAPABILITIES:
You have access to tools that can:
1. Analyze webpage structure and interactive elements
2. Inspect specific elements for interaction details
3. Assess what actions are possible on the current page
4. Validate plan feasibility and calculate confidence

TASK:
Create a structured ExecutionPlan that breaks down the user goal into specific, executable actions.

REQUIREMENTS:
1. Each action must specify: TYPE, TARGET, CONFIDENCE, FALLBACK
2. Actions must be in logical sequence
3. Include confidence scores (0-100) for each step
4. Identify potential failure points and alternatives
5. Ensure plan is achievable with current webpage state

ACTION TYPES:
- CLICK: Click on buttons, links, or interactive elements
- TYPE: Enter text into input fields
- NAVIGATE: Move to different pages or sections
- WAIT: Wait for page loading or dynamic content
- SCROLL: Scroll to make elements visible
- VERIFY: Confirm expected page state or content

OUTPUT FORMAT:
Return a structured plan with steps, confidence scores, and validation details.

Begin analysis:
""")
```

---

## 🗄️ **2. Database Schema Design**

### **ExecutionPlan Model**
```python
class ExecutionPlan(Base):
    __tablename__ = "execution_plans"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Plan Metadata
    goal_description = Column(Text, nullable=False)
    source_webpage_url = Column(String(2048), nullable=False)
    source_webpage_data = Column(JSON, nullable=False)  # Parsed webpage data used for planning
    plan_version = Column(Integer, default=1)
    
    # Plan Content
    total_steps = Column(Integer, nullable=False)
    estimated_duration_seconds = Column(Integer, nullable=False)
    overall_confidence_score = Column(Float, nullable=False)  # 0.0 - 1.0
    risk_assessment = Column(JSON, nullable=True)
    
    # Plan Status
    status = Column(Enum(PlanStatus), default=PlanStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by_user = Column(Boolean, default=False)
    
    # Planning Metadata
    planning_duration_ms = Column(Integer, nullable=True)
    llm_model_used = Column(String(100), nullable=True)
    agent_iterations = Column(Integer, nullable=True)
    planning_tokens_used = Column(Integer, nullable=True)
    
    # Relationships
    action_steps = relationship("ActionStep", back_populates="execution_plan", cascade="all, delete-orphan")
    task = relationship("Task", back_populates="execution_plans")
    user = relationship("User")

class PlanStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
```

### **ActionStep Model**
```python
class ActionStep(Base):
    __tablename__ = "action_steps"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    execution_plan_id = Column(Integer, ForeignKey("execution_plans.id"), nullable=False, index=True)
    
    # Step Identification
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(200), nullable=False)
    step_description = Column(Text, nullable=False)
    
    # Action Definition
    action_type = Column(Enum(ActionType), nullable=False)
    target_element = Column(JSON, nullable=True)  # Selector, xpath, etc.
    action_data = Column(JSON, nullable=True)     # Text to type, URL to navigate, etc.
    
    # Confidence & Validation
    confidence_score = Column(Float, nullable=False)  # 0.0 - 1.0
    expected_outcome = Column(Text, nullable=True)
    validation_criteria = Column(JSON, nullable=True)
    
    # Fallback & Error Handling
    fallback_actions = Column(JSON, nullable=True)
    timeout_seconds = Column(Integer, default=30)
    retry_count = Column(Integer, default=3)
    
    # Dependencies
    depends_on_steps = Column(JSON, nullable=True)  # List of step IDs
    conditional_logic = Column(JSON, nullable=True)
    
    # Execution Metadata
    status = Column(Enum(StepStatus), default=StepStatus.PENDING)
    executed_at = Column(DateTime, nullable=True)
    execution_duration_ms = Column(Integer, nullable=True)
    actual_outcome = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Relationships
    execution_plan = relationship("ExecutionPlan", back_populates="action_steps")

class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    WAIT = "wait"
    SCROLL = "scroll"
    VERIFY = "verify"
    SELECT = "select"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SCREENSHOT = "screenshot"

class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
```

---

## 🌐 **3. Planning API Architecture**

### **Core Planning Endpoints**

#### **POST /api/v1/plans/generate**
```python
@router.post("/generate")
async def generate_execution_plan(
    plan_request: PlanGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Generate an AI-powered execution plan for a user goal.
    
    Input:
    - task_id: ID of completed webpage parsing task
    - user_goal: Natural language description of what to accomplish
    - planning_options: Confidence threshold, risk tolerance, etc.
    
    Returns:
    - plan_id: Unique identifier for generated plan
    - status: Planning status (queued/in_progress/completed)
    - estimated_completion: When planning will be done
    """
```

#### **GET /api/v1/plans/{plan_id}**
```python
@router.get("/{plan_id}")
async def get_plan_status(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get execution plan details and current status.
    
    Returns:
    - plan_metadata: Goal, confidence, step count
    - action_steps: Detailed step-by-step breakdown
    - status: Current plan status
    - approval_required: Whether human approval is needed
    """
```

#### **POST /api/v1/plans/{plan_id}/approve**
```python
@router.post("/{plan_id}/approve")
async def approve_execution_plan(
    plan_id: int,
    approval_request: PlanApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Approve or reject a generated execution plan.
    
    Input:
    - approval_decision: approve/reject/modify
    - feedback: Optional user feedback for improvement
    - modifications: Requested changes to plan
    
    Returns:
    - status: Updated plan status
    - ready_for_execution: Whether plan is ready for Phase 2D
    """
```

### **Background Planning Service**
```python
class PlanningService:
    """Core service for AI-powered execution plan generation."""
    
    def __init__(self):
        self.agent_executor = self._initialize_langchain_agent()
        self.confidence_threshold = 0.75
        self.max_planning_time = 300  # 5 minutes
    
    async def generate_plan_async(
        self, 
        db: AsyncSession, 
        task_id: int, 
        user_goal: str, 
        planning_options: Dict
    ) -> ExecutionPlan:
        """
        Generate execution plan using LangChain ReAct agent.
        
        Process:
        1. Retrieve parsed webpage data from task
        2. Initialize agent with webpage context
        3. Execute planning workflow with goal
        4. Parse agent output into structured plan
        5. Calculate confidence scores and risk assessment
        6. Store plan in database with all metadata
        """
        
    async def validate_plan(
        self, 
        execution_plan: ExecutionPlan
    ) -> Dict[str, Any]:
        """
        Validate generated plan for feasibility and safety.
        
        Checks:
        - Element selectors are valid and unique
        - Action sequence makes logical sense
        - Confidence scores meet thresholds
        - No destructive actions without confirmation
        - Fallback strategies are viable
        """
```

---

## 🎨 **4. LangChain Integration Framework**

### **Agent Memory System**
```python
class WebAgentPlanningMemory:
    """Custom memory system for learning from planning outcomes."""
    
    def __init__(self):
        self.successful_patterns = VectorStore()  # Store successful plan patterns
        self.failure_analysis = VectorStore()    # Store failure patterns to avoid
        self.domain_knowledge = VectorStore()    # Website-specific knowledge
    
    async def store_planning_outcome(
        self,
        plan: ExecutionPlan,
        outcome: str,
        feedback: Optional[str] = None
    ):
        """Store planning outcome for future learning."""
        
    async def retrieve_similar_plans(
        self,
        goal: str,
        webpage_context: Dict
    ) -> List[Dict]:
        """Retrieve similar successful plans for reference."""
```

### **Custom Tool Integration**
```python
class WebAgentToolkit:
    """Collection of specialized tools for web task planning."""
    
    @staticmethod
    def create_tools(webpage_data: Dict) -> List[BaseTool]:
        return [
            WebpageAnalysisTool(webpage_data=webpage_data),
            ElementInspectorTool(webpage_data=webpage_data),
            ActionCapabilityAssessor(webpage_data=webpage_data),
            PlanValidatorTool(),
            ConfidenceCalculator(),
            FallbackStrategyGenerator()
        ]
```

### **Dynamic Prompt Generation**
```python
class PromptGenerator:
    """Generate context-aware prompts for different planning scenarios."""
    
    def generate_planning_prompt(
        self,
        user_goal: str,
        webpage_data: Dict,
        user_preferences: Dict
    ) -> str:
        """Create customized prompt based on goal and context."""
        
        prompt_components = [
            self._build_context_section(webpage_data),
            self._build_goal_section(user_goal),
            self._build_capability_section(webpage_data),
            self._build_constraints_section(user_preferences),
            self._build_output_format_section()
        ]
        
        return "\n\n".join(prompt_components)
```

---

## 📊 **5. Confidence & Validation System**

### **Confidence Scoring Algorithm**
```python
class ConfidenceCalculator:
    """Calculate confidence scores for plans and individual steps."""
    
    def calculate_plan_confidence(self, execution_plan: ExecutionPlan) -> float:
        """
        Calculate overall plan confidence based on:
        - Individual step confidence scores
        - Element selector reliability
        - Action sequence complexity
        - Historical success rates for similar plans
        - Webpage structure stability indicators
        """
        
    def calculate_step_confidence(self, action_step: ActionStep, webpage_data: Dict) -> float:
        """
        Calculate confidence for individual action step:
        - Element selector uniqueness and stability
        - Action type complexity and reliability
        - Required user data availability
        - Expected outcome predictability
        """
```

### **Plan Validation Framework**
```python
class PlanValidator:
    """Comprehensive validation for generated execution plans."""
    
    def validate_plan(self, execution_plan: ExecutionPlan) -> ValidationResult:
        """
        Validate plan across multiple dimensions:
        """
        
        validations = [
            self._validate_action_sequence(),
            self._validate_element_selectors(),
            self._validate_confidence_thresholds(),
            self._validate_safety_constraints(),
            self._validate_fallback_strategies(),
            self._validate_timing_and_dependencies()
        ]
        
        return ValidationResult(validations)
```

---

## 🔄 **6. Integration with Phase 2B**

### **Background Task Integration**
```python
# Extend existing background task system
def _process_plan_generation(
    task_id: int,
    user_goal: str,
    planning_options: Dict
):
    """Background task for AI plan generation (extends Phase 2B pattern)."""
    
    # Mark planning task as in progress
    await TaskStatusService.mark_task_processing(db, task_id, "planning_service")
    
    # Generate plan using LangChain agent
    execution_plan = await PlanningService.generate_plan_async(
        db, task_id, user_goal, planning_options
    )
    
    # Store results and update task status
    await TaskStatusService.complete_task(db, task_id, {
        "execution_plan_id": execution_plan.id,
        "planning_confidence": execution_plan.overall_confidence_score,
        "step_count": execution_plan.total_steps
    })
```

### **Enhanced Task Model**
```python
# Add to existing Task model
class Task(Base):
    # ... existing fields ...
    
    # Phase 2C additions
    execution_plans = relationship("ExecutionPlan", back_populates="task")
    user_goal = Column(Text, nullable=True)  # Store user's natural language goal
    planning_status = Column(Enum(PlanningStatus), nullable=True)
    requires_approval = Column(Boolean, default=True)
```

---

## 🎯 **7. Human-in-the-Loop Workflow**

### **Approval Workflow**
```python
class ApprovalWorkflow:
    """Manage human approval process for generated plans."""
    
    async def require_approval(self, execution_plan: ExecutionPlan) -> bool:
        """
        Determine if plan requires human approval based on:
        - Overall confidence score
        - Presence of sensitive actions (file uploads, payments)
        - Risk assessment results
        - User preferences for automation level
        """
        
    async def present_plan_for_approval(
        self, 
        execution_plan: ExecutionPlan
    ) -> ApprovalPresentation:
        """
        Format plan for human review with:
        - Clear step-by-step breakdown
        - Confidence indicators
        - Risk warnings
        - Alternative options
        - Estimated execution time
        """
```

---

## 📈 **8. Success Metrics & Learning**

### **Planning Quality Metrics**
- **Plan Accuracy**: How often generated plans achieve the user goal
- **Confidence Calibration**: How well confidence scores predict success
- **Planning Efficiency**: Time to generate high-quality plans
- **User Satisfaction**: Approval rates and feedback scores

### **Learning & Improvement**
```python
class PlanningImprovement:
    """Continuous improvement system for planning quality."""
    
    async def analyze_execution_outcome(
        self,
        execution_plan: ExecutionPlan,
        execution_result: ExecutionResult
    ):
        """Learn from plan execution outcomes to improve future planning."""
        
    async def update_confidence_models(self):
        """Update confidence scoring based on historical performance."""
        
    async def refine_planning_prompts(self):
        """Improve system prompts based on successful patterns."""
```

---

## 🏗️ **Implementation Architecture Summary**

### **Service Layer Structure**
```
app/services/
├── planning_service.py          # Core planning orchestration
├── langchain_agent_service.py   # LangChain agent management
├── plan_validation_service.py   # Plan quality assurance
├── confidence_scoring_service.py # Confidence calculation
└── approval_workflow_service.py # Human approval process
```

### **API Layer Structure**
```
app/api/v1/endpoints/
└── plans.py                     # Planning API endpoints
```

### **Database Migration**
```
alembic/versions/
└── 003_ai_planning_schema.py    # ExecutionPlan and ActionStep tables
```

### **LangChain Integration**
```
app/langchain/
├── agents/                      # Custom agent configurations
├── tools/                       # WebAgent-specific tools
├── prompts/                     # System prompts
└── memory/                      # Agent memory systems
```

---

## 🎉 **Phase 2C Success Criteria**

### **Input Example**
```python
user_goal = "Deploy my React app to Vercel"
webpage_data = {
    "url": "https://vercel.com/new",
    "interactive_elements": [
        {"type": "button", "text": "Import Git Repository", "confidence": 0.95},
        {"type": "input", "placeholder": "Repository URL", "confidence": 0.90},
        {"type": "button", "text": "Deploy", "confidence": 0.95}
    ]
}
```

### **Expected Output**
```python
execution_plan = ExecutionPlan(
    goal_description="Deploy my React app to Vercel",
    overall_confidence_score=0.92,
    total_steps=4,
    action_steps=[
        ActionStep(
            step_number=1,
            action_type=ActionType.CLICK,
            target_element={"selector": "button[data-testid='import-git-repo']"},
            confidence_score=0.95,
            step_description="Click 'Import Git Repository' to start deployment"
        ),
        ActionStep(
            step_number=2,
            action_type=ActionType.TYPE,
            target_element={"selector": "input[placeholder='Repository URL']"},
            action_data={"text": "https://github.com/user/my-react-app"},
            confidence_score=0.90,
            step_description="Enter GitHub repository URL"
        ),
        # ... additional steps
    ]
)
```

---

This architecture transforms WebAgent from understanding websites to intelligently reasoning about web tasks, setting the foundation for autonomous web automation in Phase 2D.