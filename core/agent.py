"""
Autonomous Agent Core Framework
A self-contained AI system for business process automation powered by LLMs.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm import LLMBackend
from tools import ToolRegistry

logger = logging.getLogger(__name__)


# Import these lazily to avoid circular imports
def _get_memory():
    from memory import MemorySystem
    return MemorySystem

def _get_planner(llm, tool_registry):
    from planning import Planner
    return Planner(llm, tool_registry)

def _get_safety():
    from safety import SafetyValidator
    return SafetyValidator

def _get_execution_result():
    from planning import ExecutionResult
    return ExecutionResult


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentConfig:
    """Configuration for the autonomous agent."""
    name: str = "autonomous_agent"
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    temperature: float = 0.7
    max_tokens: int = 4096
    max_iterations: int = 100
    max_tool_calls: int = 20
    confidence_threshold: float = 0.7
    enable_learning: bool = True
    enable_safety: bool = True
    verbose: bool = True


@dataclass
class Task:
    """Represents a task to be executed by the agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    goal: str = ""
    context: dict = field(default_factory=dict)
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response from the agent after task execution."""
    task_id: str
    state: AgentState
    result: Optional[Any] = None
    error: Optional[str] = None
    steps_executed: int = 0
    tools_used: list = field(default_factory=list)
    execution_time: float = 0.0
    confidence: float = 0.0
    needs_human_input: bool = False
    human_input_prompt: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class AutonomousAgent:
    """
    Core autonomous agent that can execute business processes.
    
    Features:
    - LLM-powered reasoning and decision making
    - Modular tool system for environment interaction
    - Hierarchical memory for context and learning
    - Planning and execution engine
    - Safety validation and governance
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self.current_task: Optional[Task] = None
        self.execution_history: list = []
        
        # Initialize core components
        self.llm = LLMBackend(
            model_name=self.config.groq_model,
            api_key=self.config.groq_api_key,
            base_url=self.config.groq_base_url,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        self.tool_registry = ToolRegistry()
        
        # Lazy load to avoid circular imports
        MemorySystem = _get_memory()
        self.memory = MemorySystem()
        
        PlannerClass = _get_planner(self.llm, self.tool_registry)
        self.planner = PlannerClass
        
        self.safety = _get_safety()() if self.config.enable_safety else None
        
        logger.info(f"Initialized AutonomousAgent: {self.config.name}")

    async def execute(self, task: Task) -> AgentResponse:
        """
        Execute a task autonomously.
        
        Args:
            task: The task to execute
            
        Returns:
            AgentResponse with results and metadata
        """
        start_time = datetime.now()
        self.current_task = task
        self.state = AgentState.THINKING
        
        try:
            # Step 1: Analyze task and retrieve relevant context
            context = await self._prepare_context(task)
            
            # Step 2: Generate execution plan
            plan = await self.planner.create_plan(task.goal, context)
            
            # Step 3: Execute plan with safety checks
            result = await self._execute_plan(plan, context)
            
            # Step 4: Learn from execution
            if self.config.enable_learning:
                await self._learn_from_execution(task, result)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            response = AgentResponse(
                task_id=task.id,
                state=AgentState.COMPLETED,
                result=result.data,
                steps_executed=result.steps_executed,
                tools_used=result.tools_used,
                execution_time=execution_time,
                confidence=result.confidence,
                metadata=result.metadata
            )
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.state = AgentState.ERROR
            response = AgentResponse(
                task_id=task.id,
                state=AgentState.ERROR,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
        
        self.execution_history.append(response)
        self.state = AgentState.IDLE
        return response

    async def _prepare_context(self, task: Task) -> dict:
        """Prepare execution context from memory and task data."""
        # Retrieve relevant semantic memory
        relevant_memories = await self.memory.retrieve(task.goal, limit=5)
        
        # Get recent execution history for context
        recent_history = self.execution_history[-3:] if self.execution_history else []
        
        context = {
            "task": {
                "id": task.id,
                "description": task.description,
                "goal": task.goal,
                "priority": task.priority
            },
            "relevant_experience": relevant_memories,
            "recent_history": [
                {
                    "task_id": h.task_id,
                    "state": h.state.value,
                    "success": h.state == AgentState.COMPLETED,
                    "tools_used": h.tools_used
                }
                for h in recent_history
            ],
            "available_tools": self.tool_registry.get_available_tools(),
            "config": {
                "max_iterations": self.config.max_iterations,
                "max_tool_calls": self.config.max_tool_calls,
                "confidence_threshold": self.config.confidence_threshold
            }
        }
        
        return context

    async def _execute_plan(self, plan, context):
        """Execute the planned steps with safety checks."""
        ExecutionResult = _get_execution_result()
        
        self.state = AgentState.EXECUTING
        executor = self.planner.create_executor()
        
        steps_executed = 0
        tools_used = []
        results = []
        
        for step in plan.steps:
            # Safety check before each step
            if self.safety:
                is_safe = await self.safety.validate_action(step, context)
                if not is_safe:
                    logger.warning(f"Step blocked by safety: {step.action}")
                    continue
            
            # Execute step
            result = await executor.execute_step(step, context)
            steps_executed += 1
            
            if result.tool_name:
                tools_used.append(result.tool_name)
            
            results.append(result)
            
            # Check if we need human input
            if result.requires_human_input:
                ExecutionResult = _get_execution_result()
                return ExecutionResult(
                    data=None,
                    success=False,
                    steps_executed=steps_executed,
                    tools_used=tools_used,
                    confidence=0.0,
                    error="Human input required",
                    requires_human_input=True,
                    human_prompt=result.human_prompt
                )
            
            # Check confidence - stop if too low
            if result.confidence < self.config.confidence_threshold:
                logger.warning(f"Low confidence: {result.confidence}")
        
        # Aggregate results
        final_result = self._aggregate_results(results)
        ExecutionResult = _get_execution_result()
        
        return ExecutionResult(
            data=final_result,
            success=True,
            steps_executed=steps_executed,
            tools_used=tools_used,
            confidence=sum(r.confidence for r in results) / len(results) if results else 0.0,
            metadata={"plan_id": plan.id, "results": [r.metadata for r in results]}
        )

    def _aggregate_results(self, results: list) -> Any:
        """Aggregate results from multiple steps."""
        if not results:
            return None
        
        from planning import StepStatus
        successful_results = [r for r in results if r.status == StepStatus.COMPLETED]
        
        if len(successful_results) == 1:
            return successful_results[0].result
        
        # Return list of successful results
        return {
            "results": [r.result for r in successful_results],
            "summary": f"Completed {len(successful_results)} steps successfully"
        }

    async def _learn_from_execution(self, task: Task, result):
        """Learn from execution for future improvement."""
        # Store experience in episodic memory
        await self.memory.store_experience(
            task=task.goal,
            outcome="success" if result.success else "failure",
            steps=result.metadata.get("results", []),
            tools_used=result.tools_used,
            confidence=result.confidence
        )
        
        logger.info(f"Learned from execution: {task.goal} - {result.success}")

    def register_tool(self, name: str, func: Callable, description: str = "", 
                      parameters: Optional[dict] = None):
        """Register a tool for the agent to use."""
        self.tool_registry.register(name, func, description, parameters)
        logger.info(f"Registered tool: {name}")

    def get_status(self) -> dict:
        """Get current agent status."""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "current_task": self.current_task.id if self.current_task else None,
            "tools_count": len(self.tool_registry.get_available_tools()),
            "history_count": len(self.execution_history)
        }
