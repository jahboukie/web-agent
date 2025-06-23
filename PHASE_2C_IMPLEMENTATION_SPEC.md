# WebAgent Phase 2C Implementation Specification: AI Brain (Planning Service)

**Version:** 1.0
**Date:** June 19, 2025
**Architect:** Claude Code
**Implementer:** Augment Code
**Priority:** HIGH

---

## 🎯 **Mission Statement**

Transform WebAgent from "understanding websites" to "intelligently reasoning about web tasks" by implementing a comprehensive AI planning service using LangChain ReAct agents. This phase gives WebAgent the ability to think, reason, and generate structured execution plans for accomplishing user goals.

**Transformation:** Semantic Understanding → Intelligent Planning

---

## 📊 **Executive Summary**

### **What Phase 2C Delivers**

WebAgent will gain the cognitive ability to:
- **Reason about user goals** using natural language processing
- **Analyze webpage structures** to identify automation opportunities
- **Generate step-by-step execution plans** with confidence scoring
- **Learn from successful patterns** to improve planning quality
- **Provide human oversight** through approval workflows

### **Success Metrics**
- ✅ Generate execution plans with >85% average confidence
- ✅ <60 seconds plan generation time for typical goals
- ✅ Human approval workflow operational
- ✅ Learning system improving plan quality over time
- ✅ Template system for common automation patterns

### **Integration Points**
- **Phase 2B Integration:** Uses parsed webpage data from background task system
- **Phase 2D Preparation:** Generated plans ready for ActionExecutor implementation
- **Human-in-the-Loop:** Approval workflow ensures quality and safety

---

## 🏗️ **Implementation Roadmap**

### **Priority 1: Core Infrastructure (Week 1)**
1. **Database Migration 003** - ExecutionPlan and AtomicAction schema
2. **LangChain Dependencies** - Install and configure LangChain ecosystem
3. **Planning Service Foundation** - Core PlanningService class and initialization
4. **API Integration** - Planning endpoints integrated with existing FastAPI app

### **Priority 2: LangChain Agent System (Week 2)**
5. **ReAct Agent Implementation** - Core planning agent with custom tools
6. **Custom Tools Development** - WebpageAnalysisTool, ElementInspectorTool, etc.
7. **Agent Memory System** - Learning from successful planning patterns
8. **Plan Validation Framework** - Safety and feasibility validation

### **Priority 3: Human Workflow (Week 3)**
9. **Approval Workflow** - Human-in-the-loop plan review and approval
10. **Confidence Scoring** - Quality assessment and auto-approval thresholds
11. **Template System** - Reusable patterns for common automation tasks
12. **Testing and Validation** - End-to-end flow testing with real scenarios

---

## 📁 **File Structure to Implement**

```
app/
├── langchain/                          # NEW: LangChain integration
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   └── planning_agent.py           # ReAct agent for plan generation
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── webpage_tools.py            # Custom tools for webpage analysis
│   │   └── base_tool.py                # Base tool class
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── planning_prompts.py         # System prompts for planning
│   ├── memory/
│   │   ├── __init__.py
│   │   └── planning_memory.py          # Agent memory system
│   └── validation/
│       ├── __init__.py
│       └── plan_validator.py           # Plan validation logic
├── models/
│   └── execution_plan.py               # ENHANCED: Phase 2C planning models
├── schemas/
│   └── planning.py                     # NEW: Planning request/response schemas
├── services/
│   └── planning_service.py             # NEW: Core planning orchestration
└── api/v1/endpoints/
    └── plans.py                        # NEW: Planning API endpoints

alembic/versions/
└── 003_ai_planning_schema.py           # NEW: Database migration for planning models
```

---

## 🛠️ **Task 1: Database Migration for AI Planning**

### **File:** `alembic/versions/003_ai_planning_schema.py`

**Objective:** Create database migration for ExecutionPlan and AtomicAction models with Phase 2C AI planning capabilities.

```python
"""Phase 2C: AI Planning Schema - ExecutionPlan and AtomicAction models

Revision ID: 003_ai_planning_schema
Revises: 002_background_tasks
Create Date: 2025-06-19

This migration adds comprehensive AI planning capabilities including:
- ExecutionPlan model with LangChain agent metadata
- AtomicAction model with detailed step information
- PlanTemplate model for reusable automation patterns
- Enhanced indexes for planning queries
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create execution_plans table
    op.create_table(
        'execution_plans',

        # Primary key and foreign keys
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),

        # Plan metadata
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('original_goal', sa.Text(), nullable=False),
        sa.Column('source_webpage_url', sa.String(2048), nullable=False),
        sa.Column('source_webpage_data', sa.JSON(), nullable=False),
        sa.Column('plan_version', sa.Integer(), nullable=False, default=1),

        # Plan content
        sa.Column('total_actions', sa.Integer(), nullable=False, default=0),
        sa.Column('estimated_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('complexity_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('risk_assessment', sa.JSON(), nullable=True),

        # AI planning metadata
        sa.Column('llm_model_used', sa.String(100), nullable=True),
        sa.Column('agent_iterations', sa.Integer(), nullable=True),
        sa.Column('planning_tokens_used', sa.Integer(), nullable=True),
        sa.Column('planning_duration_ms', sa.Integer(), nullable=True),
        sa.Column('planning_temperature', sa.Float(), nullable=True),

        # Plan classification
        sa.Column('automation_category', sa.String(100), nullable=True),
        sa.Column('requires_sensitive_actions', sa.Boolean(), nullable=False, default=False),
        sa.Column('complexity_level', sa.String(50), nullable=False, default='medium'),

        # Quality and validation
        sa.Column('plan_quality_score', sa.Float(), nullable=True),
        sa.Column('validation_passed', sa.Boolean(), nullable=False, default=False),
        sa.Column('validation_warnings', sa.JSON(), nullable=True),
        sa.Column('validation_errors', sa.JSON(), nullable=True),

        # Human approval workflow
        sa.Column('requires_approval', sa.Boolean(), nullable=False, default=True),
        sa.Column('approved_by_user', sa.Boolean(), nullable=False, default=False),
        sa.Column('approval_feedback', sa.Text(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),

        # Plan status
        sa.Column('status', sa.Enum(
            'DRAFT', 'GENERATING', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED',
            'VALIDATED', 'EXECUTING', 'COMPLETED', 'FAILED', 'CANCELLED',
            name='planstatus'
        ), nullable=False, default='DRAFT'),

        # Additional context
        sa.Column('target_domain', sa.String(255), nullable=True),
        sa.Column('starting_url', sa.String(2048), nullable=True),
        sa.Column('planning_context', sa.JSON(), nullable=True, default={}),

        # Execution tracking
        sa.Column('success_probability', sa.Float(), nullable=True),
        sa.Column('actual_success', sa.Boolean(), nullable=True),
        sa.Column('execution_success_rate', sa.Float(), nullable=True),
        sa.Column('actual_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('execution_notes', sa.Text(), nullable=True),

        # Learning and improvement
        sa.Column('similar_plans_referenced', sa.JSON(), nullable=True),
        sa.Column('learning_tags', sa.JSON(), nullable=True),
        sa.Column('user_satisfaction_score', sa.Integer(), nullable=True),

        # Error handling
        sa.Column('fallback_plans', sa.JSON(), nullable=True, default=[]),
        sa.Column('error_recovery_strategy', sa.String(100), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create atomic_actions table
    op.create_table(
        'atomic_actions',

        # Primary key and foreign keys
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('execution_plan_id', sa.Integer(), sa.ForeignKey('execution_plans.id'), nullable=False),
        sa.Column('target_element_id', sa.Integer(), sa.ForeignKey('interactive_elements.id'), nullable=True),

        # Step identification
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(200), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),

        # Action definition
        sa.Column('action_type', sa.Enum(
            'NAVIGATE', 'CLICK', 'TYPE', 'SELECT', 'UPLOAD', 'DOWNLOAD', 'WAIT',
            'SCROLL', 'SUBMIT', 'EXTRACT', 'VERIFY', 'SCREENSHOT', 'HOVER',
            'KEY_PRESS', 'DRAG_DROP', name='actiontype'
        ), nullable=False),
        sa.Column('target_selector', sa.String(1000), nullable=True),
        sa.Column('input_value', sa.Text(), nullable=True),
        sa.Column('action_data', sa.JSON(), nullable=True),

        # Enhanced element targeting
        sa.Column('element_xpath', sa.String(1000), nullable=True),
        sa.Column('element_css_selector', sa.String(500), nullable=True),
        sa.Column('element_attributes', sa.JSON(), nullable=True),
        sa.Column('element_text_content', sa.String(500), nullable=True),

        # Confidence and validation
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('expected_outcome', sa.Text(), nullable=True),
        sa.Column('validation_criteria', sa.JSON(), nullable=True),

        # Preconditions and context
        sa.Column('preconditions', sa.JSON(), nullable=True),
        sa.Column('required_page_elements', sa.JSON(), nullable=True),
        sa.Column('required_page_state', sa.JSON(), nullable=True),

        # Error handling and fallback
        sa.Column('fallback_actions', sa.JSON(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, default=30),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=False, default=2),

        # Dependencies and conditions
        sa.Column('depends_on_steps', sa.JSON(), nullable=True),
        sa.Column('conditional_logic', sa.JSON(), nullable=True),
        sa.Column('skip_if_conditions', sa.JSON(), nullable=True),

        # Action metadata
        sa.Column('is_critical', sa.Boolean(), nullable=False, default=False),
        sa.Column('requires_confirmation', sa.Boolean(), nullable=False, default=False),
        sa.Column('wait_condition', sa.String(200), nullable=True),

        # Execution status and results
        sa.Column('status', sa.Enum(
            'PENDING', 'EXECUTING', 'COMPLETED', 'FAILED', 'SKIPPED', 'RETRYING', 'BLOCKED',
            name='stepstatus'
        ), nullable=False, default='PENDING'),
        sa.Column('executed', sa.Boolean(), nullable=False, default=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_duration_ms', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),

        # Execution results
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('actual_outcome', sa.Text(), nullable=True),
        sa.Column('validation_passed', sa.Boolean(), nullable=True),

        # Screenshots and evidence
        sa.Column('before_screenshot_path', sa.String(500), nullable=True),
        sa.Column('after_screenshot_path', sa.String(500), nullable=True),
        sa.Column('screenshot_path', sa.String(500), nullable=True),

        # Quality and learning
        sa.Column('execution_confidence', sa.Float(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('performance_metrics', sa.JSON(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create plan_templates table
    op.create_table(
        'plan_templates',

        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),

        # Template metadata
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),

        # Template content
        sa.Column('template_steps', sa.JSON(), nullable=False),
        sa.Column('required_elements', sa.JSON(), nullable=False),
        sa.Column('variable_fields', sa.JSON(), nullable=True),

        # Usage and quality
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('average_confidence', sa.Float(), nullable=True),

        # Learning metadata
        sa.Column('created_from_plans', sa.JSON(), nullable=True),
        sa.Column('website_patterns', sa.JSON(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for performance
    op.create_index('idx_execution_plans_task_id', 'execution_plans', ['task_id'])
    op.create_index('idx_execution_plans_user_id', 'execution_plans', ['user_id'])
    op.create_index('idx_execution_plans_status', 'execution_plans', ['status'])
    op.create_index('idx_execution_plans_created_at', 'execution_plans', ['created_at'])

    op.create_index('idx_atomic_actions_execution_plan_id', 'atomic_actions', ['execution_plan_id'])
    op.create_index('idx_atomic_actions_step_number', 'atomic_actions', ['step_number'])
    op.create_index('idx_atomic_actions_action_type', 'atomic_actions', ['action_type'])
    op.create_index('idx_atomic_actions_status', 'atomic_actions', ['status'])

    op.create_index('idx_plan_templates_category', 'plan_templates', ['category'])
    op.create_index('idx_plan_templates_usage_count', 'plan_templates', ['usage_count'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_plan_templates_usage_count')
    op.drop_index('idx_plan_templates_category')
    op.drop_index('idx_atomic_actions_status')
    op.drop_index('idx_atomic_actions_action_type')
    op.drop_index('idx_atomic_actions_step_number')
    op.drop_index('idx_atomic_actions_execution_plan_id')
    op.drop_index('idx_execution_plans_created_at')
    op.drop_index('idx_execution_plans_status')
    op.drop_index('idx_execution_plans_user_id')
    op.drop_index('idx_execution_plans_task_id')

    # Drop tables
    op.drop_table('plan_templates')
    op.drop_table('atomic_actions')
    op.drop_table('execution_plans')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS stepstatus')
    op.execute('DROP TYPE IF EXISTS actiontype')
    op.execute('DROP TYPE IF EXISTS planstatus')
```

**Testing Requirements:**
```bash
# Apply migration
alembic upgrade head

# Test migration rollback
alembic downgrade -1
alembic upgrade head

# Verify schema
python -c "
from app.models.execution_plan import ExecutionPlan, AtomicAction, PlanTemplate
print('✅ All models imported successfully')
"
```

---

## 🛠️ **Task 2: LangChain Dependencies Installation**

### **File:** `pyproject.toml` (ENHANCEMENT)

**Objective:** Add LangChain ecosystem dependencies for AI planning capabilities.

```toml
# Add these dependencies to the existing [tool.poetry.dependencies] section

[tool.poetry.dependencies]
# ... existing dependencies ...

# Phase 2C: LangChain AI Planning Dependencies
langchain = "^0.1.0"                    # Core LangChain framework
langchain-anthropic = "^0.1.0"          # Anthropic (Claude) integration
langchain-openai = "^0.1.0"             # OpenAI integration (backup)
langchain-community = "^0.0.20"         # Community tools and integrations
langchain-experimental = "^0.0.50"      # Experimental features

# ReAct Agent and Tools
langchain-core = "^0.1.23"              # Core abstractions
faiss-cpu = "^1.7.4"                    # Vector similarity search for memory
chromadb = "^0.4.22"                    # Vector database for learning
tiktoken = "^0.5.2"                     # Token counting for usage tracking

# Additional AI/ML tools
numpy = "^1.24.0"                       # Numerical computations
scikit-learn = "^1.3.0"                 # Machine learning for confidence scoring
```

**Installation Commands:**
```bash
# Install new dependencies
poetry install

# Verify LangChain installation
python -c "
import langchain
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_react_agent
print('✅ LangChain ecosystem installed successfully')
"
```

---

## 🛠️ **Task 3: LangChain ReAct Agent Implementation**

### **File:** `app/langchain/agents/planning_agent.py`

**Objective:** Implement the core ReAct agent for AI-powered execution plan generation.

```python
from typing import Dict, List, Any, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.tools import BaseTool
import structlog
import json
import asyncio
from datetime import datetime

from app.core.config import settings
from app.langchain.prompts.planning_prompts import WEBAGENT_PLANNING_PROMPT
from app.langchain.memory.planning_memory import PlanningMemory

logger = structlog.get_logger(__name__)


class PlanningAgent:
    """
    Phase 2C: LangChain ReAct agent for intelligent execution plan generation.

    This agent uses the ReAct (Reasoning + Acting) pattern to:
    1. Analyze webpage data and user goals
    2. Reason about possible automation approaches
    3. Generate structured execution plans with confidence scoring
    4. Learn from successful patterns for improvement
    """

    def __init__(self):
        """Initialize the planning agent with LLM and memory."""
        self.llm = None
        self.agent = None
        self.agent_executor = None
        self.memory = None
        self.planning_memory = None
        self._initialized = False

    async def initialize(self):
        """Initialize LangChain components and agent."""
        if self._initialized:
            return

        try:
            # Initialize LLM (Claude 3.5 Sonnet)
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1,  # Low temperature for consistent planning
                max_tokens=4000,
                timeout=60
            )

            # Initialize conversation memory
            self.memory = ConversationBufferWindowMemory(
                k=10,  # Keep last 10 interactions
                memory_key="chat_history",
                return_messages=True
            )

            # Initialize planning memory for learning
            self.planning_memory = PlanningMemory()
            await self.planning_memory.initialize()

            self._initialized = True
            logger.info("Planning agent initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize planning agent", error=str(e))
            raise

    async def execute_planning(
        self,
        goal: str,
        context: Dict[str, Any],
        tools: List[BaseTool],
        temperature: float = 0.1,
        max_iterations: int = 15
    ) -> Dict[str, Any]:
        """
        Execute the planning workflow using ReAct agent.

        Process:
        1. Create agent with custom tools and prompt
        2. Execute agent with goal and webpage context
        3. Parse agent output into structured plan
        4. Extract metadata (iterations, tokens, etc.)

        Args:
            goal: User's natural language goal
            context: Webpage data and planning context
            tools: Custom tools for webpage analysis
            temperature: LLM temperature (0.0-1.0)
            max_iterations: Maximum agent iterations

        Returns:
            Dict containing execution plan and metadata
        """

        if not self._initialized:
            await self.initialize()

        planning_start_time = datetime.utcnow()

        try:
            # Update LLM temperature if different
            if abs(self.llm.temperature - temperature) > 0.01:
                self.llm.temperature = temperature

            # Create agent with tools and prompt
            agent = create_react_agent(
                llm=self.llm,
                tools=tools,
                prompt=self._create_planning_prompt(context)
            )

            # Create agent executor
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=self.memory,
                max_iterations=max_iterations,
                early_stopping_method="generate",
                verbose=True,
                handle_parsing_errors=True
            )

            # Prepare agent input
            agent_input = self._prepare_agent_input(goal, context)

            # Execute agent
            logger.info(
                "Executing planning agent",
                goal=goal[:100],
                max_iterations=max_iterations,
                temperature=temperature
            )

            result = await agent_executor.ainvoke(agent_input)

            # Parse and structure the result
            structured_result = await self._parse_agent_result(result, context, planning_start_time)

            # Store successful pattern in memory
            await self._store_planning_pattern(goal, context, structured_result)

            logger.info(
                "Planning agent execution completed",
                iterations_used=structured_result.get('iterations_used', 0),
                tokens_used=structured_result.get('tokens_used', 0),
                plan_confidence=structured_result.get('execution_plan', {}).get('confidence_score', 0)
            )

            return structured_result

        except Exception as e:
            logger.error("Planning agent execution failed", error=str(e), goal=goal[:100])

            # Return fallback plan structure
            return self._create_fallback_plan(goal, context, str(e))

    def _create_planning_prompt(self, context: Dict[str, Any]) -> PromptTemplate:
        """Create contextual planning prompt for the agent."""

        # Get similar successful plans from memory
        similar_plans = []  # TODO: Implement memory retrieval

        prompt_template = WEBAGENT_PLANNING_PROMPT.format(
            webpage_summary=context.get('webpage_summary', 'No webpage data available'),
            similar_patterns=self._format_similar_patterns(similar_plans)
        )

        return PromptTemplate.from_template(prompt_template)

    def _prepare_agent_input(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for agent execution."""

        return {
            'input': goal,
            'user_goal': goal,
            'webpage_url': context.get('webpage_url', 'unknown'),
            'webpage_title': context.get('webpage_title', 'unknown'),
            'total_elements': context.get('total_elements', 0),
            'interactive_elements': context.get('interactive_elements', []),
            'content_blocks': context.get('content_blocks', []),
            'planning_options': context.get('planning_options', {})
        }

    async def _parse_agent_result(
        self,
        result: Dict[str, Any],
        context: Dict[str, Any],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Parse raw agent result into structured execution plan."""

        try:
            # Extract the agent's output
            agent_output = result.get('output', '')

            # Parse the structured plan from agent output
            # Note: The agent should output JSON-formatted execution plan
            execution_plan = self._extract_execution_plan(agent_output, context)
            action_steps = self._extract_action_steps(agent_output, context)

            # Calculate metadata
            planning_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            tokens_used = self._estimate_tokens_used(result)
            iterations_used = self._count_agent_iterations(result)

            return {
                'execution_plan': execution_plan,
                'action_steps': action_steps,
                'llm_model': 'claude-3-5-sonnet-20241022',
                'iterations_used': iterations_used,
                'tokens_used': tokens_used,
                'planning_duration_ms': planning_duration_ms,
                'agent_output': agent_output,
                'success': True
            }

        except Exception as e:
            logger.error("Failed to parse agent result", error=str(e))

            # Return minimal fallback structure
            return self._create_fallback_plan(
                context.get('user_goal', 'Unknown goal'),
                context,
                f"Parse error: {str(e)}"
            )

    def _extract_execution_plan(self, agent_output: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract execution plan metadata from agent output."""

        try:
            # Look for JSON plan in agent output
            # Agent should format output as: ```json\n{plan_data}\n```

            json_start = agent_output.find('```json')
            json_end = agent_output.find('```', json_start + 7)

            if json_start != -1 and json_end != -1:
                json_content = agent_output[json_start + 7:json_end].strip()
                plan_data = json.loads(json_content)

                return {
                    'title': plan_data.get('title', f"Execute: {context.get('user_goal', 'Unknown')}"),
                    'description': plan_data.get('description', 'AI-generated execution plan'),
                    'confidence_score': float(plan_data.get('confidence_score', 0.7)),
                    'complexity_score': float(plan_data.get('complexity_score', 0.5)),
                    'estimated_duration_seconds': int(plan_data.get('estimated_duration_seconds', 60)),
                    'automation_category': plan_data.get('automation_category', 'general'),
                    'requires_sensitive_actions': bool(plan_data.get('requires_sensitive_actions', False)),
                    'complexity_level': plan_data.get('complexity_level', 'medium'),
                    'risk_assessment': plan_data.get('risk_assessment', {}),
                    'learning_tags': plan_data.get('learning_tags', [])
                }

        except Exception as e:
            logger.warning("Failed to extract structured plan from agent output", error=str(e))

        # Fallback plan metadata
        return {
            'title': f"Execute: {context.get('user_goal', 'Unknown goal')}",
            'description': 'AI-generated execution plan',
            'confidence_score': 0.5,
            'complexity_score': 0.5,
            'estimated_duration_seconds': 60,
            'automation_category': 'general',
            'requires_sensitive_actions': False,
            'complexity_level': 'medium',
            'risk_assessment': {},
            'learning_tags': []
        }

    def _extract_action_steps(self, agent_output: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract action steps from agent output."""

        try:
            # Look for steps section in agent output
            steps_start = agent_output.find('EXECUTION_STEPS:')
            if steps_start == -1:
                steps_start = agent_output.find('steps:')

            if steps_start != -1:
                steps_section = agent_output[steps_start:]

                # Parse step-by-step instructions
                steps = []
                lines = steps_section.split('\n')

                current_step = None
                for line in lines:
                    line = line.strip()

                    # Look for step numbers (1., 2., etc.)
                    if line and (line[0].isdigit() and '.' in line[:5]):
                        if current_step:
                            steps.append(current_step)

                        current_step = self._parse_step_line(line, len(steps) + 1)

                    elif current_step and line:
                        # Additional details for current step
                        self._enhance_step_details(current_step, line)

                # Add final step
                if current_step:
                    steps.append(current_step)

                return steps

        except Exception as e:
            logger.warning("Failed to extract action steps from agent output", error=str(e))

        # Fallback: Create basic steps based on goal
        return self._create_fallback_steps(context.get('user_goal', 'Unknown goal'))

    def _parse_step_line(self, line: str, step_number: int) -> Dict[str, Any]:
        """Parse individual step line into structured step data."""

        # Remove step number prefix
        step_content = line.split('.', 1)[1].strip() if '.' in line else line

        # Determine action type from content
        action_type = 'click'
        if any(word in step_content.lower() for word in ['type', 'enter', 'input']):
            action_type = 'type'
        elif any(word in step_content.lower() for word in ['navigate', 'go to', 'visit']):
            action_type = 'navigate'
        elif any(word in step_content.lower() for word in ['wait', 'pause']):
            action_type = 'wait'
        elif any(word in step_content.lower() for word in ['scroll']):
            action_type = 'scroll'
        elif any(word in step_content.lower() for word in ['select', 'choose']):
            action_type = 'select'

        return {
            'step_name': f"Step {step_number}",
            'description': step_content,
            'action_type': action_type,
            'confidence_score': 0.7,  # Default confidence
            'timeout_seconds': 30,
            'max_retries': 3,
            'is_critical': False,
            'requires_confirmation': False
        }

    def _enhance_step_details(self, step: Dict[str, Any], detail_line: str):
        """Enhance step with additional details from agent output."""

        detail_lower = detail_line.lower()

        # Look for selector information
        if 'selector:' in detail_lower or 'element:' in detail_lower:
            selector_part = detail_line.split(':', 1)[1].strip()
            step['target_selector'] = selector_part

        # Look for input value
        elif 'value:' in detail_lower or 'text:' in detail_lower:
            value_part = detail_line.split(':', 1)[1].strip()
            step['input_value'] = value_part

        # Look for confidence
        elif 'confidence:' in detail_lower:
            try:
                conf_str = detail_line.split(':', 1)[1].strip().replace('%', '')
                step['confidence_score'] = float(conf_str) / 100.0
            except:
                pass

    def _create_fallback_steps(self, goal: str) -> List[Dict[str, Any]]:
        """Create basic fallback steps when agent parsing fails."""

        return [
            {
                'step_name': 'Step 1',
                'description': f'Navigate to target page for: {goal}',
                'action_type': 'navigate',
                'confidence_score': 0.5,
                'timeout_seconds': 30,
                'max_retries': 3,
                'is_critical': True,
                'requires_confirmation': False
            }
        ]

    def _create_fallback_plan(self, goal: str, context: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create fallback plan when agent execution fails."""

        return {
            'execution_plan': {
                'title': f"Fallback plan: {goal}",
                'description': f'Fallback plan due to error: {error}',
                'confidence_score': 0.3,
                'complexity_score': 0.8,
                'estimated_duration_seconds': 120,
                'automation_category': 'fallback',
                'requires_sensitive_actions': True,  # Be conservative
                'complexity_level': 'expert',
                'risk_assessment': {'error': error},
                'learning_tags': ['fallback', 'error']
            },
            'action_steps': self._create_fallback_steps(goal),
            'llm_model': 'claude-3-5-sonnet-20241022',
            'iterations_used': 0,
            'tokens_used': 0,
            'planning_duration_ms': 0,
            'success': False,
            'error': error
        }

    def _estimate_tokens_used(self, result: Dict[str, Any]) -> int:
        """Estimate tokens used during agent execution."""

        # Simple estimation based on input/output length
        # In production, use tiktoken for accurate counting

        input_text = str(result.get('input', ''))
        output_text = str(result.get('output', ''))

        # Rough estimation: ~4 characters per token
        estimated_tokens = len(input_text + output_text) // 4

        return max(estimated_tokens, 100)  # Minimum estimate

    def _count_agent_iterations(self, result: Dict[str, Any]) -> int:
        """Count the number of agent iterations from result."""

        # Look for iteration indicators in intermediate steps
        intermediate_steps = result.get('intermediate_steps', [])
        return len(intermediate_steps)

    def _format_similar_patterns(self, similar_plans: List[Dict[str, Any]]) -> str:
        """Format similar successful patterns for prompt context."""

        if not similar_plans:
            return "No similar patterns available."

        formatted = []
        for i, plan in enumerate(similar_plans[:3], 1):  # Top 3 patterns
            formatted.append(f"{i}. {plan.get('summary', 'Pattern')} (confidence: {plan.get('confidence', 'unknown')})")

        return "\n".join(formatted)

    async def _store_planning_pattern(
        self,
        goal: str,
        context: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """Store successful planning pattern for future learning."""

        try:
            if result.get('success') and self.planning_memory:
                pattern_data = {
                    'goal': goal,
                    'webpage_domain': context.get('webpage_url', '').split('/')[2] if context.get('webpage_url') else 'unknown',
                    'execution_plan': result.get('execution_plan', {}),
                    'action_steps': result.get('action_steps', []),
                    'success': True,
                    'timestamp': datetime.utcnow().isoformat()
                }

                await self.planning_memory.store_pattern(pattern_data)

        except Exception as e:
            logger.warning("Failed to store planning pattern", error=str(e))
```

**Testing Requirements:**
```python
# Test file: tests/test_planning_agent.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.langchain.agents.planning_agent import PlanningAgent

@pytest.mark.asyncio
async def test_planning_agent_initialization():
    """Test planning agent initialization."""
    agent = PlanningAgent()
    await agent.initialize()
    assert agent._initialized is True
    assert agent.llm is not None

@pytest.mark.asyncio
async def test_execute_planning_basic():
    """Test basic planning execution."""
    agent = PlanningAgent()
    await agent.initialize()

    goal = "Click the submit button"
    context = {
        'webpage_url': 'https://example.com',
        'webpage_title': 'Test Page',
        'total_elements': 5,
        'interactive_elements': [
            {'element_type': 'button', 'text': 'Submit', 'confidence': 0.9}
        ]
    }

    result = await agent.execute_planning(goal, context, [])

    assert result['success'] is True
    assert 'execution_plan' in result
    assert 'action_steps' in result
    assert len(result['action_steps']) > 0
```

---

## 🛠️ **Task 4: Custom LangChain Tools Implementation**

### **File:** `app/langchain/tools/webpage_tools.py`

**Objective:** Implement custom LangChain tools for webpage analysis and action planning.

```python
from typing import Dict, List, Any, Optional
from langchain_core.tools import BaseTool
from pydantic import Field
import structlog
import json

logger = structlog.get_logger(__name__)


class WebpageAnalysisTool(BaseTool):
    """
    Custom LangChain tool for analyzing parsed webpage data.

    This tool provides the agent with comprehensive webpage understanding
    capabilities including structure analysis, element categorization,
    and automation feasibility assessment.
    """

    name: str = "webpage_analyzer"
    description: str = """Analyze semantic webpage data to understand page structure, interactive elements,
    and automation possibilities. Use this tool to get comprehensive insights about the current webpage
    before planning actions."""

    webpage_data: Dict[str, Any] = Field(description="Parsed webpage data from Phase 2B")

    def _run(self, query: str = "") -> str:
        """Analyze webpage data and return insights."""

        try:
            web_page = self.webpage_data.get('web_page', {})
            interactive_elements = self.webpage_data.get('interactive_elements', [])
            content_blocks = self.webpage_data.get('content_blocks', [])

            analysis = {
                'page_info': {
                    'url': web_page.get('url', 'unknown'),
                    'title': web_page.get('title', 'unknown'),
                    'domain': web_page.get('domain', 'unknown'),
                    'total_interactive_elements': len(interactive_elements),
                    'total_content_blocks': len(content_blocks)
                },
                'element_analysis': self._analyze_interactive_elements(interactive_elements),
                'content_analysis': self._analyze_content_blocks(content_blocks),
                'automation_assessment': self._assess_automation_feasibility(interactive_elements)
            }

            return json.dumps(analysis, indent=2)

        except Exception as e:
            logger.error("Webpage analysis failed", error=str(e))
            return f"Analysis failed: {str(e)}"

    def _analyze_interactive_elements(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze interactive elements for automation potential."""

        element_types = {}
        high_confidence_elements = []
        automation_ready = []

        for element in elements:
            # Count element types
            element_type = element.get('element_type', 'unknown')
            element_types[element_type] = element_types.get(element_type, 0) + 1

            # Identify high-confidence elements
            confidence = element.get('interaction_confidence', 0)
            if confidence > 0.8:
                high_confidence_elements.append({
                    'type': element_type,
                    'text': element.get('text_content', '')[:50],
                    'confidence': confidence,
                    'selector': element.get('css_selector', '')
                })

            # Assess automation readiness
            if (confidence > 0.7 and
                element.get('css_selector') and
                element_type in ['button', 'input', 'select', 'link']):
                automation_ready.append(element)

        return {
            'element_type_distribution': element_types,
            'high_confidence_elements': high_confidence_elements[:10],  # Top 10
            'automation_ready_count': len(automation_ready),
            'total_elements': len(elements)
        }

    def _analyze_content_blocks(self, content_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze content blocks for context understanding."""

        block_types = {}
        important_content = []

        for block in content_blocks:
            # Count block types
            block_type = block.get('block_type', 'unknown')
            block_types[block_type] = block_types.get(block_type, 0) + 1

            # Identify important content
            importance = block.get('semantic_importance', 0)
            if importance > 0.7:
                important_content.append({
                    'type': block_type,
                    'content': block.get('text_content', '')[:100],
                    'importance': importance
                })

        return {
            'content_type_distribution': block_types,
            'important_content': important_content[:5],  # Top 5
            'total_blocks': len(content_blocks)
        }

    def _assess_automation_feasibility(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall automation feasibility for the webpage."""

        total_elements = len(elements)
        if total_elements == 0:
            return {'feasibility_score': 0.0, 'reasoning': 'No interactive elements found'}

        # Calculate feasibility metrics
        high_confidence_count = len([e for e in elements if e.get('interaction_confidence', 0) > 0.8])
        has_selectors_count = len([e for e in elements if e.get('css_selector')])
        automation_types_count = len([e for e in elements if e.get('element_type') in ['button', 'input', 'select', 'link']])

        # Calculate overall feasibility score
        confidence_score = high_confidence_count / total_elements
        selector_score = has_selectors_count / total_elements
        type_score = automation_types_count / total_elements

        feasibility_score = (confidence_score + selector_score + type_score) / 3

        # Determine feasibility level
        if feasibility_score > 0.8:
            level = 'excellent'
        elif feasibility_score > 0.6:
            level = 'good'
        elif feasibility_score > 0.4:
            level = 'moderate'
        elif feasibility_score > 0.2:
            level = 'challenging'
        else:
            level = 'difficult'

        return {
            'feasibility_score': round(feasibility_score, 3),
            'feasibility_level': level,
            'high_confidence_elements': high_confidence_count,
            'elements_with_selectors': has_selectors_count,
            'automation_ready_types': automation_types_count,
            'reasoning': f'{level.title()} automation feasibility based on element confidence and selector availability'
        }


class ElementInspectorTool(BaseTool):
    """
    Custom LangChain tool for deep inspection of specific webpage elements.

    This tool allows the agent to examine individual elements in detail
    to determine interaction methods, confidence levels, and potential issues.
    """

    name: str = "element_inspector"
    description: str = """Inspect specific webpage elements to determine interaction methods and confidence levels.
    Provide element selector, text content, or element type to get detailed analysis."""

    webpage_data: Dict[str, Any] = Field(description="Parsed webpage data from Phase 2B")

    def _run(self, element_query: str) -> str:
        """Inspect specific elements based on query."""

        try:
            interactive_elements = self.webpage_data.get('interactive_elements', [])

            # Find matching elements based on query
            matching_elements = self._find_matching_elements(interactive_elements, element_query)

            if not matching_elements:
                return f"No elements found matching query: {element_query}"

            # Analyze each matching element
            element_analyses = []
            for element in matching_elements[:5]:  # Limit to top 5 matches
                analysis = self._analyze_element(element)
                element_analyses.append(analysis)

            result = {
                'query': element_query,
                'matching_elements_count': len(matching_elements),
                'element_analyses': element_analyses
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error("Element inspection failed", error=str(e))
            return f"Inspection failed: {str(e)}"

    def _find_matching_elements(self, elements: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Find elements matching the query."""

        query_lower = query.lower()
        matching = []

        for element in elements:
            # Check text content
            text_content = element.get('text_content', '').lower()
            if query_lower in text_content:
                matching.append(element)
                continue

            # Check element type
            element_type = element.get('element_type', '').lower()
            if query_lower in element_type:
                matching.append(element)
                continue

            # Check CSS selector
            css_selector = element.get('css_selector', '').lower()
            if query_lower in css_selector:
                matching.append(element)
                continue

            # Check attributes
            attributes = element.get('attributes', {})
            for attr_value in attributes.values():
                if isinstance(attr_value, str) and query_lower in attr_value.lower():
                    matching.append(element)
                    break

        # Sort by interaction confidence
        matching.sort(key=lambda e: e.get('interaction_confidence', 0), reverse=True)

        return matching

    def _analyze_element(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual element for interaction potential."""

        element_type = element.get('element_type', 'unknown')
        confidence = element.get('interaction_confidence', 0)

        analysis = {
            'element_type': element_type,
            'text_content': element.get('text_content', '')[:100],
            'css_selector': element.get('css_selector', ''),
            'xpath': element.get('xpath', ''),
            'interaction_confidence': confidence,
            'attributes': element.get('attributes', {}),
            'position': element.get('position', {}),
            'recommended_actions': self._get_recommended_actions(element),
            'potential_issues': self._identify_potential_issues(element),
            'interaction_method': self._determine_interaction_method(element)
        }

        return analysis

    def _get_recommended_actions(self, element: Dict[str, Any]) -> List[str]:
        """Get recommended actions for the element."""

        element_type = element.get('element_type', '').lower()
        actions = []

        if element_type == 'button':
            actions.append('CLICK')
        elif element_type == 'input':
            input_type = element.get('attributes', {}).get('type', 'text').lower()
            if input_type in ['text', 'email', 'password', 'search']:
                actions.append('TYPE')
            elif input_type in ['checkbox', 'radio']:
                actions.append('CLICK')
            elif input_type == 'file':
                actions.append('UPLOAD')
        elif element_type == 'select':
            actions.append('SELECT')
        elif element_type == 'link':
            actions.append('CLICK')
        elif element_type == 'textarea':
            actions.append('TYPE')

        return actions

    def _identify_potential_issues(self, element: Dict[str, Any]) -> List[str]:
        """Identify potential issues with element interaction."""

        issues = []

        # Check confidence level
        confidence = element.get('interaction_confidence', 0)
        if confidence < 0.5:
            issues.append('Low interaction confidence')

        # Check for selectors
        if not element.get('css_selector') and not element.get('xpath'):
            issues.append('No reliable selectors available')

        # Check visibility
        position = element.get('position', {})
        if position.get('width', 0) == 0 or position.get('height', 0) == 0:
            issues.append('Element may be hidden or have zero dimensions')

        # Check for common problematic attributes
        attributes = element.get('attributes', {})
        if attributes.get('disabled'):
            issues.append('Element is disabled')
        if attributes.get('readonly'):
            issues.append('Element is readonly')
        if 'hidden' in attributes.get('class', '').lower():
            issues.append('Element may be hidden via CSS class')

        return issues

    def _determine_interaction_method(self, element: Dict[str, Any]) -> Dict[str, str]:
        """Determine the best interaction method for the element."""

        element_type = element.get('element_type', '').lower()
        css_selector = element.get('css_selector', '')
        xpath = element.get('xpath', '')
        confidence = element.get('interaction_confidence', 0)

        # Prefer CSS selector if available and confidence is high
        if css_selector and confidence > 0.7:
            return {
                'method': 'css_selector',
                'selector': css_selector,
                'confidence': 'high'
            }

        # Use XPath as fallback
        elif xpath:
            return {
                'method': 'xpath',
                'selector': xpath,
                'confidence': 'medium'
            }

        # Last resort: text-based selection
        else:
            text_content = element.get('text_content', '')
            if text_content and len(text_content) < 50:
                return {
                    'method': 'text_content',
                    'selector': text_content,
                    'confidence': 'low'
                }

        return {
            'method': 'none',
            'selector': '',
            'confidence': 'very_low'
        }


class ActionCapabilityAssessor(BaseTool):
    """
    Custom LangChain tool for assessing what actions are possible on the current webpage.

    This tool helps the agent understand the full range of automation possibilities
    and identify the most reliable interaction paths for achieving the user's goal.
    """

    name: str = "action_assessor"
    description: str = """Assess what actions (CLICK, TYPE, NAVIGATE, etc.) are possible given the current webpage state.
    Use this to understand automation capabilities before planning specific steps."""

    webpage_data: Dict[str, Any] = Field(description="Parsed webpage data from Phase 2B")

    def _run(self, goal: str = "") -> str:
        """Assess action capabilities for the webpage."""

        try:
            interactive_elements = self.webpage_data.get('interactive_elements', [])
            web_page = self.webpage_data.get('web_page', {})

            # Assess available actions
            capabilities = {
                'navigation_capabilities': self._assess_navigation_capabilities(web_page, interactive_elements),
                'interaction_capabilities': self._assess_interaction_capabilities(interactive_elements),
                'form_capabilities': self._assess_form_capabilities(interactive_elements),
                'content_capabilities': self._assess_content_capabilities(interactive_elements),
                'goal_specific_assessment': self._assess_goal_specific_capabilities(goal, interactive_elements)
            }

            return json.dumps(capabilities, indent=2)

        except Exception as e:
            logger.error("Action capability assessment failed", error=str(e))
            return f"Assessment failed: {str(e)}"

    def _assess_navigation_capabilities(self, web_page: Dict[str, Any], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess navigation possibilities."""

        # Count navigation elements
        links = [e for e in elements if e.get('element_type') == 'link']
        buttons_with_navigation = [
            e for e in elements
            if e.get('element_type') == 'button' and
            any(word in e.get('text_content', '').lower() for word in ['go', 'next', 'continue', 'submit'])
        ]

        current_url = web_page.get('url', '')

        return {
            'current_url': current_url,
            'links_available': len(links),
            'navigation_buttons': len(buttons_with_navigation),
            'can_navigate_external': len([l for l in links if not current_url.split('/')[2] in l.get('attributes', {}).get('href', '')]) > 0,
            'navigation_confidence': min(1.0, (len(links) + len(buttons_with_navigation)) / 10)
        }

    def _assess_interaction_capabilities(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess general interaction capabilities."""

        action_counts = {
            'clickable_elements': 0,
            'input_fields': 0,
            'dropdown_selects': 0,
            'file_uploads': 0,
            'checkboxes': 0,
            'radio_buttons': 0
        }

        high_confidence_actions = []

        for element in elements:
            element_type = element.get('element_type', '')
            confidence = element.get('interaction_confidence', 0)

            if element_type in ['button', 'link']:
                action_counts['clickable_elements'] += 1
                if confidence > 0.8:
                    high_confidence_actions.append('CLICK')

            elif element_type == 'input':
                input_type = element.get('attributes', {}).get('type', 'text')
                if input_type in ['text', 'email', 'password', 'search', 'textarea']:
                    action_counts['input_fields'] += 1
                    if confidence > 0.8:
                        high_confidence_actions.append('TYPE')
                elif input_type == 'file':
                    action_counts['file_uploads'] += 1
                    if confidence > 0.8:
                        high_confidence_actions.append('UPLOAD')
                elif input_type == 'checkbox':
                    action_counts['checkboxes'] += 1
                elif input_type == 'radio':
                    action_counts['radio_buttons'] += 1

            elif element_type == 'select':
                action_counts['dropdown_selects'] += 1
                if confidence > 0.8:
                    high_confidence_actions.append('SELECT')

        return {
            'action_counts': action_counts,
            'high_confidence_actions': list(set(high_confidence_actions)),
            'total_interactive_elements': len(elements),
            'interaction_complexity': self._calculate_interaction_complexity(action_counts)
        }

    def _assess_form_capabilities(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess form interaction capabilities."""

        forms_detected = []

        # Group elements by potential forms (simplified detection)
        input_elements = [e for e in elements if e.get('element_type') == 'input']
        submit_buttons = [
            e for e in elements
            if e.get('element_type') == 'button' and
            any(word in e.get('text_content', '').lower() for word in ['submit', 'send', 'save', 'create', 'register', 'login'])
        ]

        if input_elements and submit_buttons:
            forms_detected.append({
                'estimated_form_fields': len(input_elements),
                'submit_buttons': len(submit_buttons),
                'form_completion_feasibility': min(1.0, len([e for e in input_elements if e.get('interaction_confidence', 0) > 0.7]) / len(input_elements))
            })

        return {
            'forms_detected': len(forms_detected),
            'form_details': forms_detected,
            'total_form_fields': len(input_elements),
            'can_complete_forms': len(forms_detected) > 0
        }

    def _assess_content_capabilities(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess content extraction and verification capabilities."""

        text_elements = [e for e in elements if e.get('text_content')]

        return {
            'text_extraction_available': len(text_elements) > 0,
            'extractable_text_elements': len(text_elements),
            'verification_possible': True,  # Can always verify page state
            'screenshot_possible': True    # Screenshots always available
        }

    def _assess_goal_specific_capabilities(self, goal: str, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess capabilities specific to the user's goal."""

        if not goal:
            return {'assessment': 'No specific goal provided'}

        goal_lower = goal.lower()
        relevant_elements = []
        suggested_actions = []

        # Look for elements related to the goal
        for element in elements:
            text_content = element.get('text_content', '').lower()
            element_type = element.get('element_type', '')

            # Check if element text relates to goal
            goal_words = goal_lower.split()
            if any(word in text_content for word in goal_words if len(word) > 3):
                relevant_elements.append({
                    'element_type': element_type,
                    'text': element.get('text_content', '')[:50],
                    'confidence': element.get('interaction_confidence', 0),
                    'relevance_score': len([w for w in goal_words if w in text_content]) / len(goal_words)
                })

        # Sort by relevance and confidence
        relevant_elements.sort(key=lambda e: e['relevance_score'] * e['confidence'], reverse=True)

        # Suggest actions based on goal keywords
        if any(word in goal_lower for word in ['click', 'press', 'button']):
            suggested_actions.append('CLICK')
        if any(word in goal_lower for word in ['type', 'enter', 'input', 'fill']):
            suggested_actions.append('TYPE')
        if any(word in goal_lower for word in ['select', 'choose', 'pick']):
            suggested_actions.append('SELECT')
        if any(word in goal_lower for word in ['upload', 'attach', 'file']):
            suggested_actions.append('UPLOAD')
        if any(word in goal_lower for word in ['navigate', 'go to', 'visit']):
            suggested_actions.append('NAVIGATE')

        goal_feasibility = 0.5  # Default
        if relevant_elements:
            # Calculate feasibility based on relevant elements
            avg_confidence = sum(e['confidence'] for e in relevant_elements[:3]) / min(len(relevant_elements), 3)
            avg_relevance = sum(e['relevance_score'] for e in relevant_elements[:3]) / min(len(relevant_elements), 3)
            goal_feasibility = (avg_confidence + avg_relevance) / 2

        return {
            'goal': goal,
            'relevant_elements_found': len(relevant_elements),
            'top_relevant_elements': relevant_elements[:3],
            'suggested_actions': suggested_actions,
            'goal_feasibility_score': round(goal_feasibility, 3),
            'feasibility_assessment': 'high' if goal_feasibility > 0.7 else 'medium' if goal_feasibility > 0.4 else 'low'
        }

    def _calculate_interaction_complexity(self, action_counts: Dict[str, int]) -> str:
        """Calculate overall interaction complexity."""

        total_actions = sum(action_counts.values())

        if total_actions == 0:
            return 'none'
        elif total_actions <= 3:
            return 'simple'
        elif total_actions <= 10:
            return 'moderate'
        elif total_actions <= 20:
            return 'complex'
        else:
            return 'very_complex'
```

**Testing Requirements:**
```python
# Test file: tests/test_webpage_tools.py

import pytest
from app.langchain.tools.webpage_tools import WebpageAnalysisTool, ElementInspectorTool, ActionCapabilityAssessor

def test_webpage_analysis_tool():
    """Test webpage analysis tool."""

    webpage_data = {
        'web_page': {
            'url': 'https://example.com',
            'title': 'Test Page',
            'domain': 'example.com'
        },
        'interactive_elements': [
            {
                'element_type': 'button',
                'text_content': 'Submit',
                'interaction_confidence': 0.9,
                'css_selector': 'button.submit'
            }
        ],
        'content_blocks': [
            {
                'block_type': 'heading',
                'text_content': 'Welcome',
                'semantic_importance': 0.8
            }
        ]
    }

    tool = WebpageAnalysisTool(webpage_data=webpage_data)
    result = tool._run()

    assert 'page_info' in result
    assert 'element_analysis' in result
    assert '"total_interactive_elements": 1' in result

def test_element_inspector_tool():
    """Test element inspector tool."""

    webpage_data = {
        'interactive_elements': [
            {
                'element_type': 'button',
                'text_content': 'Submit Form',
                'interaction_confidence': 0.9,
                'css_selector': 'button#submit'
            }
        ]
    }

    tool = ElementInspectorTool(webpage_data=webpage_data)
    result = tool._run("submit")

    assert 'matching_elements_count' in result
    assert 'element_analyses' in result

def test_action_capability_assessor():
    """Test action capability assessor."""

    webpage_data = {
        'web_page': {'url': 'https://example.com'},
        'interactive_elements': [
            {
                'element_type': 'input',
                'attributes': {'type': 'text'},
                'interaction_confidence': 0.8
            },
            {
                'element_type': 'button',
                'text_content': 'Submit',
                'interaction_confidence': 0.9
            }
        ]
    }

    tool = ActionCapabilityAssessor(webpage_data=webpage_data)
    result = tool._run("fill form and submit")

    assert 'interaction_capabilities' in result
    assert 'goal_specific_assessment' in result
```

---

## 🛠️ **Task 5: Plan Validation Framework**

### **File:** `app/langchain/validation/plan_validator.py`

**Objective:** Implement comprehensive plan validation for safety, feasibility, and quality assurance.

```python
from typing import Dict, List, Any, Optional
from app.models.execution_plan import ExecutionPlan, AtomicAction
import structlog
import re

logger = structlog.get_logger(__name__)


class PlanValidator:
    """
    Phase 2C: Comprehensive validation framework for AI-generated execution plans.

    This validator ensures that generated plans are:
    1. Safe (no destructive or malicious actions)
    2. Feasible (selectors are valid, actions make sense)
    3. High-quality (confidence scores are calibrated)
    4. Compliant (follows user preferences and constraints)
    """

    def __init__(self):
        """Initialize the plan validator."""
        self.confidence_threshold = 0.6
        self.max_plan_complexity = 20  # Maximum number of steps
        self.sensitive_actions = ['UPLOAD', 'DOWNLOAD', 'SUBMIT']
        self.destructive_keywords = ['delete', 'remove', 'clear', 'reset', 'destroy']

    async def validate_plan(self, execution_plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Comprehensive plan validation returning detailed results.

        Args:
            execution_plan: The ExecutionPlan to validate

        Returns:
            Dict containing validation results with is_valid, confidence_score,
            warnings, errors, and detailed validation breakdowns
        """

        try:
            validation_results = {
                'is_valid': True,
                'confidence_score': 1.0,
                'warnings': [],
                'errors': [],
                'element_validation': {},
                'sequence_validation': {},
                'safety_validation': {},
                'recommendations': []
            }

            # Run all validation checks
            await self._validate_plan_metadata(execution_plan, validation_results)
            await self._validate_action_sequence(execution_plan, validation_results)
            await self._validate_element_selectors(execution_plan, validation_results)
            await self._validate_safety_constraints(execution_plan, validation_results)
            await self._validate_confidence_scores(execution_plan, validation_results)
            await self._validate_complexity_limits(execution_plan, validation_results)

            # Calculate overall confidence and validity
            validation_results['confidence_score'] = self._calculate_validation_confidence(validation_results)
            validation_results['is_valid'] = len(validation_results['errors']) == 0

            # Generate recommendations
            validation_results['recommendations'] = self._generate_recommendations(validation_results)

            logger.info(
                "Plan validation completed",
                plan_id=execution_plan.id,
                is_valid=validation_results['is_valid'],
                confidence=validation_results['confidence_score'],
                warnings_count=len(validation_results['warnings']),
                errors_count=len(validation_results['errors'])
            )

            return validation_results

        except Exception as e:
            logger.error("Plan validation failed", plan_id=execution_plan.id, error=str(e))

            return {
                'is_valid': False,
                'confidence_score': 0.0,
                'warnings': [],
                'errors': [f"Validation process failed: {str(e)}"],
                'element_validation': {},
                'sequence_validation': {},
                'safety_validation': {},
                'recommendations': ['Manual review required due to validation failure']
            }

    async def _validate_plan_metadata(self, plan: ExecutionPlan, results: Dict[str, Any]):
        """Validate plan metadata and basic structure."""

        # Check required fields
        if not plan.original_goal or len(plan.original_goal.strip()) < 10:
            results['errors'].append("Plan goal is missing or too short")

        if plan.total_actions == 0:
            results['errors'].append("Plan has no action steps")

        if plan.confidence_score < 0.0 or plan.confidence_score > 1.0:
            results['errors'].append("Plan confidence score is out of valid range (0.0-1.0)")

        if plan.estimated_duration_seconds <= 0:
            results['warnings'].append("Plan has invalid estimated duration")

        # Check for required source data
        if not plan.source_webpage_data:
            results['errors'].append("Plan is missing source webpage data")

        # Validate plan version and status
        if plan.plan_version < 1:
            results['warnings'].append("Plan version should be >= 1")

    async def _validate_action_sequence(self, plan: ExecutionPlan, results: Dict[str, Any]):
        """Validate the logical sequence of actions."""

        sequence_validation = {
            'step_numbering_valid': True,
            'logical_flow_valid': True,
            'dependencies_valid': True,
            'issues': []
        }

        actions = plan.atomic_actions
        if not actions:
            results['errors'].append("Plan has no action steps to validate")
            return

        # Check step numbering
        expected_step = 1
        for action in sorted(actions, key=lambda a: a.step_number):
            if action.step_number != expected_step:
                sequence_validation['step_numbering_valid'] = False
                sequence_validation['issues'].append(f"Step numbering gap: expected {expected_step}, found {action.step_number}")
            expected_step += 1

        # Check logical action flow
        action_types = [action.action_type for action in sorted(actions, key=lambda a: a.step_number)]

        # Check for illogical sequences
        for i in range(len(action_types) - 1):
            current_action = action_types[i]
            next_action = action_types[i + 1]

            # TYPE should not be followed by TYPE on different elements
            if current_action == 'TYPE' and next_action == 'TYPE':
                sequence_validation['issues'].append(f"Consecutive TYPE actions at steps {i+1} and {i+2} may be inefficient")

            # NAVIGATE should typically be early in sequence
            if current_action != 'NAVIGATE' and next_action == 'NAVIGATE' and i > 2:
                sequence_validation['issues'].append(f"NAVIGATE action at step {i+2} seems late in sequence")

        # Check dependencies
        for action in actions:
            if action.depends_on_steps:
                for dep_step in action.depends_on_steps:
                    if not any(a.step_number == dep_step for a in actions):
                        sequence_validation['dependencies_valid'] = False
                        sequence_validation['issues'].append(f"Step {action.step_number} depends on non-existent step {dep_step}")

        # Add warnings/errors based on validation
        if not sequence_validation['step_numbering_valid']:
            results['warnings'].append("Action step numbering is not sequential")

        if not sequence_validation['dependencies_valid']:
            results['errors'].append("Action dependencies reference non-existent steps")

        if sequence_validation['issues']:
            results['warnings'].extend(sequence_validation['issues'][:3])  # Limit to first 3 issues

        results['sequence_validation'] = sequence_validation

    async def _validate_element_selectors(self, plan: ExecutionPlan, results: Dict[str, Any]):
        """Validate element selectors for reliability."""

        element_validation = {
            'selectors_present': 0,
            'selectors_missing': 0,
            'css_selectors_valid': 0,
            'xpath_selectors_valid': 0,
            'selector_issues': []
        }

        for action in plan.atomic_actions:
            # Skip actions that don't need selectors
            if action.action_type in ['WAIT', 'SCREENSHOT', 'NAVIGATE']:
                continue

            has_selector = bool(action.target_selector or action.element_css_selector or action.element_xpath)

            if has_selector:
                element_validation['selectors_present'] += 1

                # Validate CSS selectors
                if action.element_css_selector:
                    if self._is_valid_css_selector(action.element_css_selector):
                        element_validation['css_selectors_valid'] += 1
                    else:
                        element_validation['selector_issues'].append(f"Step {action.step_number}: Invalid CSS selector")

                # Validate XPath selectors
                if action.element_xpath:
                    if self._is_valid_xpath_selector(action.element_xpath):
                        element_validation['xpath_selectors_valid'] += 1
                    else:
                        element_validation['selector_issues'].append(f"Step {action.step_number}: Invalid XPath selector")

                # Check for overly specific selectors
                if action.element_css_selector and action.element_css_selector.count('>') > 3:
                    element_validation['selector_issues'].append(f"Step {action.step_number}: CSS selector may be too specific")

            else:
                element_validation['selectors_missing'] += 1
                element_validation['selector_issues'].append(f"Step {action.step_number}: No element selector provided")

        # Add warnings/errors based on validation
        if element_validation['selectors_missing'] > 0:
            results['errors'].append(f"{element_validation['selectors_missing']} actions are missing element selectors")

        if len(element_validation['selector_issues']) > 3:
            results['warnings'].append("Multiple selector quality issues detected")

        results['element_validation'] = element_validation

    async def _validate_safety_constraints(self, plan: ExecutionPlan, results: Dict[str, Any]):
        """Validate plan for safety and security constraints."""

        safety_validation = {
            'has_sensitive_actions': False,
            'has_destructive_actions': False,
            'requires_approval': False,
            'safety_issues': []
        }

        for action in plan.atomic_actions:
            # Check for sensitive actions
            if action.action_type in self.sensitive_actions:
                safety_validation['has_sensitive_actions'] = True
                safety_validation['safety_issues'].append(f"Step {action.step_number}: Sensitive action {action.action_type}")

            # Check for potentially destructive language
            description_lower = action.description.lower()
            step_name_lower = action.step_name.lower()

            for destructive_word in self.destructive_keywords:
                if destructive_word in description_lower or destructive_word in step_name_lower:
                    safety_validation['has_destructive_actions'] = True
                    safety_validation['safety_issues'].append(f"Step {action.step_number}: Potentially destructive action detected")
                    break

            # Check input values for suspicious content
            if action.input_value:
                input_lower = action.input_value.lower()

                # Check for script injection attempts
                if any(script_tag in input_lower for script_tag in ['<script', 'javascript:', 'onerror=']):
                    safety_validation['safety_issues'].append(f"Step {action.step_number}: Suspicious input content detected")

                # Check for file system paths
                if any(path_pattern in input_lower for path_pattern in ['../', 'c:\\', '/etc/', '/root/']):
                    safety_validation['safety_issues'].append(f"Step {action.step_number}: File system path in input")

        # Determine if approval is required
        safety_validation['requires_approval'] = (
            safety_validation['has_sensitive_actions'] or
            safety_validation['has_destructive_actions'] or
            plan.requires_sensitive_actions
        )

        # Add warnings/errors based on safety validation
        if safety_validation['has_destructive_actions']:
            results['warnings'].append("Plan contains potentially destructive actions")

        if safety_validation['has_sensitive_actions'] and not plan.requires_approval:
            results['warnings'].append("Plan contains sensitive actions but approval is not required")

        if len(safety_validation['safety_issues']) > 5:
            results['errors'].append("Too many safety issues detected")

        results['safety_validation'] = safety_validation

    async def _validate_confidence_scores(self, plan: ExecutionPlan, results: Dict[str, Any]):
        """Validate confidence scores for calibration."""

        # Check overall plan confidence
        if plan.confidence_score < self.confidence_threshold:
            results['warnings'].append(f"Plan confidence ({plan.confidence_score:.2f}) below threshold ({self.confidence_threshold})")

        # Check action confidence scores
        low_confidence_actions = []
        high_confidence_actions = []
        confidence_sum = 0

        for action in plan.atomic_actions:
            confidence_sum += action.confidence_score

            if action.confidence_score < 0.5:
                low_confidence_actions.append(action.step_number)
            elif action.confidence_score > 0.95:
                high_confidence_actions.append(action.step_number)

        # Calculate average action confidence
        avg_action_confidence = confidence_sum / len(plan.atomic_actions) if plan.atomic_actions else 0

        # Compare plan confidence with action confidence average
        confidence_diff = abs(plan.confidence_score - avg_action_confidence)
        if confidence_diff > 0.2:
            results['warnings'].append("Plan confidence not aligned with average action confidence")

        # Report low confidence actions
        if low_confidence_actions:
            results['warnings'].append(f"Low confidence actions at steps: {low_confidence_actions}")

        # Suspicious if too many actions have very high confidence
        if len(high_confidence_actions) > len(plan.atomic_actions) * 0.8:
            results['warnings'].append("Unusually high confidence scores may indicate overconfidence")

    async def _validate_complexity_limits(self, plan: ExecutionPlan, results: Dict[str, Any]):
        """Validate plan complexity doesn't exceed limits."""

        if plan.total_actions > self.max_plan_complexity:
            results['errors'].append(f"Plan has {plan.total_actions} steps, exceeding maximum of {self.max_plan_complexity}")

        # Check for overly complex individual steps
        complex_steps = []
        for action in plan.atomic_actions:
            complexity_score = 0

            # Multiple selectors increase complexity
            if action.element_css_selector and action.element_xpath:
                complexity_score += 1

            # Long input values increase complexity
            if action.input_value and len(action.input_value) > 100:
                complexity_score += 1

            # Complex conditional logic increases complexity
            if action.conditional_logic and len(str(action.conditional_logic)) > 200:
                complexity_score += 1

            # Multiple fallback actions increase complexity
            if action.fallback_actions and len(action.fallback_actions) > 2:
                complexity_score += 1

            if complexity_score >= 3:
                complex_steps.append(action.step_number)

        if complex_steps:
            results['warnings'].append(f"Complex steps detected: {complex_steps}")

    def _is_valid_css_selector(self, selector: str) -> bool:
        """Validate CSS selector syntax."""

        try:
            # Basic validation - check for common invalid patterns
            if not selector or not selector.strip():
                return False

            # Check for obvious syntax errors
            if selector.count('[') != selector.count(']'):
                return False

            if selector.count('(') != selector.count(')'):
                return False

            # Check for invalid characters at start
            if selector.startswith(('>', '+', '~')):
                return False

            # Check for empty parts
            if '..' in selector or '##' in selector:
                return False

            return True

        except Exception:
            return False

    def _is_valid_xpath_selector(self, xpath: str) -> bool:
        """Validate XPath selector syntax."""

        try:
            # Basic validation - check for common invalid patterns
            if not xpath or not xpath.strip():
                return False

            # XPath should start with / or //
            if not xpath.startswith(('/', '.')):
                return False

            # Check for balanced brackets
            if xpath.count('[') != xpath.count(']'):
                return False

            if xpath.count('(') != xpath.count(')'):
                return False

            return True

        except Exception:
            return False

    def _calculate_validation_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall validation confidence score."""

        confidence = 1.0

        # Reduce confidence for each error (more severe)
        confidence -= len(results['errors']) * 0.3

        # Reduce confidence for each warning (less severe)
        confidence -= len(results['warnings']) * 0.1

        # Factor in specific validation results
        element_validation = results.get('element_validation', {})
        if element_validation.get('selectors_missing', 0) > 0:
            confidence -= 0.2

        safety_validation = results.get('safety_validation', {})
        if safety_validation.get('has_destructive_actions', False):
            confidence -= 0.3

        # Ensure confidence stays within bounds
        return max(0.0, min(1.0, confidence))

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on validation results."""

        recommendations = []

        # Recommendations based on errors
        if any('selector' in error.lower() for error in results['errors']):
            recommendations.append("Review and fix element selectors before execution")

        if any('step' in error.lower() for error in results['errors']):
            recommendations.append("Fix action step sequence and dependencies")

        # Recommendations based on warnings
        if any('confidence' in warning.lower() for warning in results['warnings']):
            recommendations.append("Consider manual review due to low confidence scores")

        if any('sensitive' in warning.lower() for warning in results['warnings']):
            recommendations.append("Require human approval for sensitive actions")

        if any('complex' in warning.lower() for warning in results['warnings']):
            recommendations.append("Consider breaking down complex steps")

        # General recommendations
        if results['confidence_score'] < 0.7:
            recommendations.append("Plan requires human review before execution")

        if len(results['warnings']) > 5:
            recommendations.append("Multiple issues detected - comprehensive review recommended")

        # Default recommendation if no specific issues
        if not recommendations:
            recommendations.append("Plan appears valid - proceed with normal approval workflow")

        return recommendations[:5]  # Limit to top 5 recommendations
```

**Testing Requirements:**
```python
# Test file: tests/test_plan_validator.py

import pytest
from app.langchain.validation.plan_validator import PlanValidator
from app.models.execution_plan import ExecutionPlan, AtomicAction, ActionType, StepStatus

@pytest.mark.asyncio
async def test_plan_validator_valid_plan():
    """Test validator with a valid plan."""

    validator = PlanValidator()

    # Create a valid execution plan
    plan = ExecutionPlan(
        task_id=1,
        user_id=1,
        original_goal="Click the submit button",
        source_webpage_url="https://example.com",
        source_webpage_data={"web_page": {"title": "Test"}},
        confidence_score=0.8,
        total_actions=1
    )

    # Add a valid action
    action = AtomicAction(
        execution_plan_id=1,
        step_number=1,
        step_name="Click Submit",
        description="Click the submit button",
        action_type=ActionType.CLICK,
        element_css_selector="button#submit",
        confidence_score=0.8
    )
    plan.atomic_actions = [action]

    result = await validator.validate_plan(plan)

    assert result['is_valid'] is True
    assert result['confidence_score'] > 0.5
    assert len(result['errors']) == 0

@pytest.mark.asyncio
async def test_plan_validator_invalid_selectors():
    """Test validator with invalid selectors."""

    validator = PlanValidator()

    plan = ExecutionPlan(
        task_id=1,
        user_id=1,
        original_goal="Click button",
        source_webpage_url="https://example.com",
        source_webpage_data={"web_page": {"title": "Test"}},
        confidence_score=0.8,
        total_actions=1
    )

    # Add action with missing selector
    action = AtomicAction(
        execution_plan_id=1,
        step_number=1,
        step_name="Click",
        description="Click something",
        action_type=ActionType.CLICK,
        confidence_score=0.8
    )
    plan.atomic_actions = [action]

    result = await validator.validate_plan(plan)

    assert result['is_valid'] is False
    assert len(result['errors']) > 0
    assert any('selector' in error.lower() for error in result['errors'])

@pytest.mark.asyncio
async def test_plan_validator_safety_issues():
    """Test validator with safety issues."""

    validator = PlanValidator()

    plan = ExecutionPlan(
        task_id=1,
        user_id=1,
        original_goal="Delete all files",
        source_webpage_url="https://example.com",
        source_webpage_data={"web_page": {"title": "Test"}},
        confidence_score=0.8,
        total_actions=1
    )

    # Add potentially destructive action
    action = AtomicAction(
        execution_plan_id=1,
        step_number=1,
        step_name="Delete Files",
        description="Delete all user files permanently",
        action_type=ActionType.CLICK,
        element_css_selector="button.delete",
        confidence_score=0.8
    )
    plan.atomic_actions = [action]

    result = await validator.validate_plan(plan)

    assert len(result['warnings']) > 0
    assert result['safety_validation']['has_destructive_actions'] is True
```

---

## 🛠️ **Task 6: System Prompts for Planning**

### **File:** `app/langchain/prompts/planning_prompts.py`

**Objective:** Create comprehensive system prompts for guiding the LangChain ReAct agent in plan generation.

```python
from langchain.prompts import PromptTemplate

# Main planning prompt template for ReAct agent
WEBAGENT_PLANNING_PROMPT = """You are WebAgent's AI Planning Service, an expert at analyzing websites and creating executable automation plans.

ROLE:
You are a specialized AI agent that generates step-by-step execution plans for web automation tasks. You analyze webpage structures, understand user goals, and create detailed, executable plans that can be carried out by automation systems.

CURRENT CONTEXT:
- User Goal: {user_goal}
- Current Webpage: {webpage_url}
- Webpage Summary: {webpage_summary}
- Available Tools: webpage_analyzer, element_inspector, action_assessor

CAPABILITIES:
You have access to tools that can:
1. webpage_analyzer: Analyze overall webpage structure and capabilities
2. element_inspector: Inspect specific elements for interaction details
3. action_assessor: Assess what actions are possible on the webpage

TASK:
Create a structured ExecutionPlan that breaks down the user goal into specific, executable actions.

PLANNING PROCESS:
1. ANALYZE: Use your tools to understand the webpage and identify relevant elements
2. REASON: Think through the logical sequence of actions needed
3. PLAN: Generate a detailed step-by-step execution plan
4. VALIDATE: Ensure each step is feasible and safe

OUTPUT REQUIREMENTS:
You must provide your response in this exact format:

```json
{{
  "title": "Clear, descriptive title for the plan",
  "description": "Brief description of what this plan accomplishes",
  "confidence_score": 0.85,
  "complexity_score": 0.6,
  "estimated_duration_seconds": 45,
  "automation_category": "form_submission|navigation|content_extraction|general",
  "requires_sensitive_actions": false,
  "complexity_level": "simple|medium|complex|expert",
  "risk_assessment": {{
    "risk_level": "low|medium|high",
    "risk_factors": ["list", "of", "risk", "factors"],
    "mitigation_strategies": ["list", "of", "mitigation", "strategies"]
  }},
  "learning_tags": ["tag1", "tag2", "tag3"]
}}
```

EXECUTION_STEPS:
1. Step Name: Clear description of the action
   Action: CLICK|TYPE|NAVIGATE|SELECT|WAIT|SCROLL|VERIFY|UPLOAD|DOWNLOAD
   Target: CSS selector or XPath for the element
   Value: Text to input (if applicable)
   Confidence: 0.0-1.0 confidence score
   Expected: What should happen after this step

2. [Continue for each step...]

ACTION TYPES AVAILABLE:
- CLICK: Click on buttons, links, or interactive elements
- TYPE: Enter text into input fields
- NAVIGATE: Move to different pages or URLs
- SELECT: Choose options from dropdowns or select elements
- WAIT: Wait for page loading or specific conditions
- SCROLL: Scroll to make elements visible
- VERIFY: Confirm expected page state or content
- UPLOAD: Upload files through file input elements
- DOWNLOAD: Download files or content
- HOVER: Hover over elements to reveal hidden content
- KEY_PRESS: Press specific keyboard keys
- DRAG_DROP: Drag and drop operations

CONFIDENCE SCORING GUIDELINES:
- 0.9-1.0: Very high confidence - element clearly identified, action straightforward
- 0.7-0.89: High confidence - element likely correct, standard action
- 0.5-0.69: Medium confidence - element identified but may have alternatives
- 0.3-0.49: Low confidence - element unclear or action complex
- 0.0-0.29: Very low confidence - significant uncertainty

SAFETY GUIDELINES:
1. Never create plans that could be destructive or harmful
2. Be cautious with file uploads, downloads, and form submissions
3. Avoid actions that could compromise security or privacy
4. Flag sensitive actions for human approval
5. Provide clear expected outcomes for verification

QUALITY STANDARDS:
1. Each step must have a clear, specific target element
2. Actions must be in logical sequence
3. Include fallback strategies for critical steps
4. Provide realistic confidence scores
5. Ensure plan is actually achievable with given webpage

SIMILAR SUCCESSFUL PATTERNS:
{similar_patterns}

Remember: You are creating plans that will be executed by automation systems. Be precise, practical, and safe in your planning.

Begin your analysis and planning:"""

# Specialized prompts for different automation categories

FORM_SUBMISSION_PROMPT = """You are planning a form submission workflow. Focus on:
1. Identifying all required form fields
2. Determining the correct input sequence
3. Validating form completion before submission
4. Handling form validation errors

Key considerations:
- Check for required fields and validation rules
- Plan for error handling and retry logic
- Ensure form is fully filled before submission
- Consider multi-step forms or wizards"""

NAVIGATION_PROMPT = """You are planning a navigation workflow. Focus on:
1. Identifying navigation paths and links
2. Planning efficient route to target content
3. Handling dynamic content and loading states
4. Managing authentication or access controls

Key considerations:
- Plan for page loading delays
- Handle redirects and authentication
- Account for dynamic menu structures
- Plan verification of successful navigation"""

CONTENT_EXTRACTION_PROMPT = """You are planning a content extraction workflow. Focus on:
1. Identifying target content elements
2. Planning extraction sequence and methods
3. Handling dynamic or paginated content
4. Ensuring complete data capture

Key considerations:
- Plan for content loading delays
- Handle pagination or infinite scroll
- Extract structured vs unstructured content
- Verify extraction completeness"""

E_COMMERCE_PROMPT = """You are planning an e-commerce interaction workflow. Focus on:
1. Product search and selection process
2. Shopping cart and checkout workflow
3. Payment and shipping information
4. Order confirmation and tracking

Key considerations:
- Handle product variants and options
- Manage cart state and quantities
- Be extremely careful with payment actions
- Verify order details before submission"""

# Error recovery and fallback prompts

FALLBACK_PLANNING_PROMPT = """You are creating a fallback plan due to primary planning failure.

SITUATION: The primary planning process encountered an error or produced an invalid plan.
ERROR CONTEXT: {error_details}

FALLBACK STRATEGY:
1. Create a simplified, conservative plan
2. Use basic actions with high confidence
3. Include manual verification steps
4. Flag for human review and approval

GUIDELINES:
- Keep the plan simple and safe
- Use generic selectors when possible
- Include verification steps after each action
- Set conservative confidence scores
- Require human approval for execution

Focus on safety and reliability over efficiency."""

PLAN_REFINEMENT_PROMPT = """You are refining an existing execution plan based on feedback.

ORIGINAL PLAN: {original_plan}
FEEDBACK: {user_feedback}
ISSUES IDENTIFIED: {validation_issues}

REFINEMENT OBJECTIVES:
1. Address specific feedback points
2. Fix validation issues
3. Improve confidence scores where possible
4. Maintain plan feasibility

GUIDELINES:
- Preserve working parts of the original plan
- Focus changes on problematic areas
- Explain refinements in plan description
- Ensure changes don't introduce new issues"""

# Tool-specific guidance prompts

WEBPAGE_ANALYSIS_GUIDANCE = """When using the webpage_analyzer tool:

1. Always start with this tool to understand the overall page structure
2. Look for automation feasibility indicators
3. Identify element types and distributions
4. Assess page complexity and interaction potential

Ask yourself:
- What types of interactions are possible?
- How reliable are the available elements?
- What is the overall automation feasibility?
- Are there any obvious obstacles or challenges?"""

ELEMENT_INSPECTION_GUIDANCE = """When using the element_inspector tool:

1. Inspect elements mentioned in the user goal first
2. Look for elements with high confidence scores
3. Verify selector reliability and uniqueness
4. Check for alternative interaction methods

Ask yourself:
- Can this element be reliably targeted?
- What interaction method is most reliable?
- Are there fallback selectors available?
- Does this element behavior match expectations?"""

ACTION_ASSESSMENT_GUIDANCE = """When using the action_assessor tool:

1. Pass the user goal to get specific capability assessment
2. Review available action types for the webpage
3. Identify goal-specific interaction opportunities
4. Assess overall goal feasibility

Ask yourself:
- What actions are needed to achieve the goal?
- Which actions are most reliable on this page?
- Are there any missing capabilities for the goal?
- What is the overall feasibility of success?"""

# Create prompt templates
MAIN_PLANNING_TEMPLATE = PromptTemplate.from_template(WEBAGENT_PLANNING_PROMPT)
FORM_SUBMISSION_TEMPLATE = PromptTemplate.from_template(FORM_SUBMISSION_PROMPT)
NAVIGATION_TEMPLATE = PromptTemplate.from_template(NAVIGATION_PROMPT)
CONTENT_EXTRACTION_TEMPLATE = PromptTemplate.from_template(CONTENT_EXTRACTION_PROMPT)
E_COMMERCE_TEMPLATE = PromptTemplate.from_template(E_COMMERCE_PROMPT)
FALLBACK_TEMPLATE = PromptTemplate.from_template(FALLBACK_PLANNING_PROMPT)
REFINEMENT_TEMPLATE = PromptTemplate.from_template(PLAN_REFINEMENT_PROMPT)
```

**Testing Requirements:**
```python
# Test file: tests/test_planning_prompts.py

import pytest
from app.langchain.prompts.planning_prompts import MAIN_PLANNING_TEMPLATE, FORM_SUBMISSION_TEMPLATE

def test_main_planning_template():
    """Test main planning prompt template."""

    prompt = MAIN_PLANNING_TEMPLATE.format(
        user_goal="Click the submit button",
        webpage_url="https://example.com",
        webpage_summary="Simple form page with submit button",
        similar_patterns="No similar patterns available"
    )

    assert "Click the submit button" in prompt
    assert "https://example.com" in prompt
    assert "webpage_analyzer" in prompt
    assert "EXECUTION_STEPS:" in prompt

def test_specialized_prompts():
    """Test specialized prompt templates."""

    form_prompt = FORM_SUBMISSION_TEMPLATE
    assert "form submission workflow" in form_prompt
    assert "required form fields" in form_prompt

    # Verify all expected sections are present
    assert "Key considerations" in form_prompt
    assert "validation" in form_prompt
```

---

## 📈 **Success Metrics and Validation**

### **Phase 2C Success Criteria**

1. **Planning Quality Metrics:**
   - Generate plans with >85% average confidence scores
   - <60 seconds plan generation time for typical goals
   - >90% plan validation pass rate
   - Human approval workflow operational

2. **Integration Success:**
   - Seamless integration with Phase 2B background task system
   - Real-time progress tracking for plan generation
   - Error handling and graceful degradation
   - Database migration successful without data loss

3. **API Functionality:**
   - All planning endpoints operational and documented
   - Request/response schemas validated
   - Authentication and authorization working
   - Background task processing integrated

4. **Learning and Improvement:**
   - Template system for common automation patterns
   - Memory system storing successful planning patterns
   - Plan validation providing actionable feedback
   - User feedback collection and integration

### **Testing Strategy**

```bash
# 1. Database Migration Testing
alembic upgrade head
python -c "from app.models.execution_plan import ExecutionPlan; print('✅ Migration successful')"

# 2. LangChain Dependencies Testing
python -c "from langchain_anthropic import ChatAnthropic; print('✅ LangChain ready')"

# 3. Service Integration Testing
python -c "from app.services.planning_service import planning_service; print('✅ Planning service ready')"

# 4. API Endpoint Testing
curl -X POST "http://localhost:8000/api/v1/plans/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1, "user_goal": "Click the submit button"}'

# 5. End-to-End Flow Testing
python validation_tests/test_phase2c_flow.py
```

---

## 🎯 **Implementation Priority Guide**

### **Week 1: Core Infrastructure**
- **Day 1-2:** Database migration and schema validation
- **Day 3-4:** LangChain dependencies and basic agent setup
- **Day 5-7:** Planning service foundation and API integration

### **Week 2: AI Agent System**
- **Day 1-3:** ReAct agent implementation and custom tools
- **Day 4-5:** Plan validation framework and safety constraints
- **Day 6-7:** System prompts and agent memory system

### **Week 3: Human Workflow & Polish**
- **Day 1-2:** Approval workflow and confidence scoring
- **Day 3-4:** Template system and learning capabilities
- **Day 5-7:** End-to-end testing and documentation

---

## 💡 **Key Success Factors**

1. **Claude API Configuration:** Ensure Anthropic API key is properly configured for Claude 3.5 Sonnet
2. **Memory Management:** Implement efficient memory systems for learning from successful patterns
3. **Error Handling:** Comprehensive error handling for agent failures and timeouts
4. **Human Oversight:** Robust approval workflow for quality assurance and safety
5. **Performance Optimization:** Efficient plan generation within target time limits

---

## 🚀 **Next Phase Integration**

Phase 2C prepares WebAgent for Phase 2D (Action Execution) by:
- **Structured Plans:** ExecutionPlan and AtomicAction models ready for execution
- **Confidence Scores:** Reliable quality indicators for execution decisions
- **Safety Validation:** Plans pre-validated for safe execution
- **Human Approval:** Quality assurance workflow established
- **Learning System:** Pattern recognition for improved execution planning

**Phase 2C Output → Phase 2D Input:** Approved ExecutionPlan with validated AtomicAction steps ready for browser automation execution.

---

This comprehensive specification provides Augment Code with everything needed to implement Phase 2C successfully, transforming WebAgent into an intelligent planning system capable of reasoning about web automation tasks.
