"""
LangChain ReAct agent for intelligent execution plan generation.

This module implements the core planning agent that uses ReAct (Reasoning + Acting)
pattern to analyze webpage data and generate structured execution plans.
"""

from typing import Dict, List, Any, Optional
import json
import asyncio
import structlog
from datetime import datetime

# LangChain imports
try:
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain.memory import ConversationBufferWindowMemory
    from langchain_anthropic import ChatAnthropic
    from langchain_core.prompts import PromptTemplate
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError as e:
    # Graceful fallback if LangChain is not installed
    structlog.get_logger(__name__).warning("LangChain not available", error=str(e))
    create_react_agent = None
    AgentExecutor = None
    ConversationBufferWindowMemory = None
    ChatAnthropic = None
    PromptTemplate = None

from app.core.config import settings
from app.langchain.tools.webpage_tools import WebpageAnalysisTool, ElementInspectorTool, ActionCapabilityAssessor
from app.langchain.prompts.planning_prompts import WEBAGENT_PLANNING_PROMPT
from app.langchain.memory.planning_memory import PlanningMemory

logger = structlog.get_logger(__name__)


class PlanningAgent:
    """
    LangChain ReAct agent for intelligent execution plan generation.
    
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
        self.planning_memory = PlanningMemory()
        self._initialized = False
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    async def initialize(self) -> None:
        """Initialize the LangChain components."""
        if self._initialized:
            return
        
        try:
            # Check if LangChain is available
            if ChatAnthropic is None:
                raise ImportError("LangChain components not available")
            
            # Initialize LLM
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                temperature=0.1,
                max_tokens=4000,
                anthropic_api_key=settings.ANTHROPIC_API_KEY
            )
            
            # Initialize memory
            self.memory = ConversationBufferWindowMemory(
                k=10,  # Remember last 10 interactions
                memory_key="chat_history",
                return_messages=True
            )
            
            self._initialized = True
            self.logger.info("Planning agent initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize planning agent", error=str(e))
            raise
    
    async def execute_planning(
        self,
        goal: str,
        context: Dict[str, Any],
        tools: List[Any],
        temperature: float = 0.1,
        max_iterations: int = 15
    ) -> Dict[str, Any]:
        """
        Execute the planning workflow using ReAct agent.
        
        Args:
            goal: User's goal description
            context: Planning context including webpage data
            tools: List of tools available to the agent
            temperature: LLM temperature for planning
            max_iterations: Maximum agent iterations
            
        Returns:
            Generated execution plan and metadata
        """
        if not self._initialized:
            await self.initialize()
        
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
            self.logger.info(
                "Executing planning agent",
                goal=goal[:100],
                max_iterations=max_iterations,
                temperature=temperature
            )
            
            start_time = datetime.utcnow()
            
            # Run the agent
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                agent_executor.invoke,
                agent_input
            )
            
            end_time = datetime.utcnow()
            planning_duration = int((end_time - start_time).total_seconds() * 1000)
            
            # Parse and structure the result
            structured_result = await self._parse_agent_result(
                result, goal, context, planning_duration, temperature, max_iterations
            )
            
            self.logger.info(
                "Planning agent execution completed",
                duration_ms=planning_duration,
                iterations_used=structured_result.get('agent_iterations', 0)
            )
            
            return structured_result
            
        except Exception as e:
            self.logger.error("Planning agent execution failed", error=str(e))
            raise
    
    def _create_planning_prompt(self, context: Dict[str, Any]) -> PromptTemplate:
        """Create the planning prompt template."""
        prompt_template = WEBAGENT_PLANNING_PROMPT
        
        return PromptTemplate(
            input_variables=["webpage_context", "user_goal", "agent_scratchpad", "tools", "tool_names"],
            template=prompt_template + "\n\nTools available: {tools}\nTool names: {tool_names}\n\n{agent_scratchpad}"
        )
    
    def _prepare_agent_input(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the agent."""
        return {
            "user_goal": goal,
            "webpage_context": json.dumps(context, indent=2)
        }
    
    async def _parse_agent_result(
        self,
        agent_result: Dict[str, Any],
        goal: str,
        context: Dict[str, Any],
        planning_duration: int,
        temperature: float,
        max_iterations: int
    ) -> Dict[str, Any]:
        """Parse and structure the agent result."""
        try:
            # Extract the agent's output
            agent_output = agent_result.get('output', '')
            
            # Try to parse JSON from the output
            execution_plan = None
            action_steps = []
            
            # Look for JSON in the output
            json_start = agent_output.find('{')
            json_end = agent_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                try:
                    json_content = agent_output[json_start:json_end]
                    parsed_json = json.loads(json_content)
                    
                    if 'execution_plan' in parsed_json:
                        execution_plan = parsed_json['execution_plan']
                        action_steps = parsed_json.get('action_steps', [])
                    else:
                        # The entire JSON might be the execution plan
                        execution_plan = parsed_json
                        action_steps = parsed_json.get('action_steps', [])
                        
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse JSON from agent output")
            
            # If no valid JSON found, create a basic plan structure
            if not execution_plan:
                execution_plan = {
                    'title': f"Plan for: {goal[:50]}...",
                    'description': 'Generated execution plan',
                    'original_goal': goal,
                    'confidence_score': 0.5,
                    'complexity_score': 0.5,
                    'estimated_duration_seconds': 60,
                    'requires_sensitive_actions': False,
                    'automation_category': 'general'
                }
                
                # Try to extract action steps from text
                action_steps = self._extract_actions_from_text(agent_output)
            
            # Add metadata
            execution_plan.update({
                'llm_model_used': 'claude-3-5-sonnet-20241022',
                'planning_duration_ms': planning_duration,
                'planning_temperature': temperature,
                'agent_iterations': max_iterations,  # We don't have exact count
                'planning_tokens_used': len(agent_output) // 4,  # Rough estimate
                'source_webpage_url': context.get('url', ''),
                'planning_context': context
            })
            
            return {
                'execution_plan': execution_plan,
                'action_steps': action_steps,
                'agent_output': agent_output,
                'agent_iterations': max_iterations,
                'planning_duration_ms': planning_duration,
                'success': True
            }
            
        except Exception as e:
            self.logger.error("Failed to parse agent result", error=str(e))
            
            # Return a fallback structure
            return {
                'execution_plan': {
                    'title': f"Failed plan for: {goal[:50]}...",
                    'description': f"Plan generation failed: {str(e)}",
                    'original_goal': goal,
                    'confidence_score': 0.0,
                    'complexity_score': 1.0,
                    'estimated_duration_seconds': 0,
                    'requires_sensitive_actions': False,
                    'automation_category': 'failed'
                },
                'action_steps': [],
                'agent_output': agent_result.get('output', ''),
                'agent_iterations': 0,
                'planning_duration_ms': planning_duration,
                'success': False,
                'error': str(e)
            }
    
    def _extract_actions_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract action steps from text output as fallback."""
        actions = []
        
        # Simple pattern matching for common action descriptions
        lines = text.split('\n')
        step_number = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for action-like patterns
            action_type = 'unknown'
            if any(word in line.lower() for word in ['click', 'press', 'tap']):
                action_type = 'click'
            elif any(word in line.lower() for word in ['type', 'enter', 'input']):
                action_type = 'type'
            elif any(word in line.lower() for word in ['navigate', 'go to', 'visit']):
                action_type = 'navigate'
            elif any(word in line.lower() for word in ['wait', 'pause']):
                action_type = 'wait'
            elif any(word in line.lower() for word in ['submit', 'send']):
                action_type = 'submit'
            
            if action_type != 'unknown':
                actions.append({
                    'step_number': step_number,
                    'step_name': f"Step {step_number}",
                    'description': line,
                    'action_type': action_type,
                    'confidence_score': 0.5,
                    'timeout_seconds': 30,
                    'is_critical': False,
                    'requires_confirmation': False
                })
                step_number += 1
        
        return actions
