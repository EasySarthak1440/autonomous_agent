"""
Planning and Execution Engine
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(Enum):
    ACTION = "action"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    WAIT = "wait"
    PARALLEL = "parallel"


@dataclass
class ExecutionStep:
    """A single step in an execution plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_type: StepType = StepType.ACTION
    action: str = ""
    parameters: dict = field(default_factory=dict)
    depends_on: list = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    confidence: float = 0.0
    requires_human_input: bool = False
    human_prompt: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """A complete execution plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    steps: list[ExecutionStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    estimated_duration: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result from executing a plan."""
    success: bool
    data: Any = None
    steps_executed: int = 0
    tools_used: list = field(default_factory=list)
    confidence: float = 0.0
    error: Optional[str] = None
    requires_human_input: bool = False
    human_prompt: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class Planner:
    """Plans and executes tasks using LLM and tools."""
    
    def __init__(self, llm, tool_registry):
        self.llm = llm
        self.tool_registry = tool_registry
    
    async def create_plan(self, goal: str, context: dict) -> ExecutionPlan:
        """
        Create an execution plan for a goal.
        
        Uses LLM to decompose goal into steps.
        """
        available_tools = self.tool_registry.get_available_tools()
        
        tools_description = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in available_tools
        ])
        
        system_prompt = f"""You are a planning AI. Given a goal and context, create a step-by-step execution plan.

Available tools:
{tools_description}

Guidelines:
1. Break down the goal into small, executable steps
2. Each step should use exactly one tool
3. Consider dependencies between steps
4. Include retry logic for critical steps
5. Estimate confidence for each step

Respond with a JSON execution plan."""
        
        user_prompt = f"""Goal: {goal}

Context:
{json.dumps(context, indent=2)}

Create an execution plan as JSON:
{{
    "goal": "...",
    "steps": [
        {{
            "action": "tool_name",
            "parameters": {{...}},
            "depends_on": [],
            "max_retries": 3,
            "timeout": 300
        }}
    ],
    "estimated_duration": 0.0
}}"""

        try:
            # Try structured output first
            plan_data = await self.llm.generate_with_structured_output(
                user_prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action": {"type": "string"},
                                    "parameters": {"type": "object"},
                                    "depends_on": {"type": "array", "items": {"type": "string"}},
                                    "max_retries": {"type": "number"},
                                    "timeout": {"type": "number"}
                                },
                                "required": ["action", "parameters"]
                            }
                        },
                        "estimated_duration": {"type": "number"}
                    },
                    "required": ["goal", "steps"]
                },
                system_prompt=system_prompt
            )
            
            plan = ExecutionPlan(
                goal=plan_data.get("goal", goal),
                estimated_duration=plan_data.get("estimated_duration", 0.0)
            )
            
            for step_data in plan_data.get("steps", []):
                step = ExecutionStep(
                    action=step_data.get("action", ""),
                    parameters=step_data.get("parameters", {}),
                    depends_on=step_data.get("depends_on", []),
                    max_retries=step_data.get("max_retries", 3),
                    timeout=step_data.get("timeout", 300)
                )
                plan.steps.append(step)
            
            logger.info(f"Created plan with {len(plan.steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            # Fallback: single step with the goal as action
            return ExecutionPlan(
                goal=goal,
                steps=[ExecutionStep(action="execute_command", parameters={"command": goal})]
            )
    
    def create_executor(self) -> 'PlanExecutor':
        """Create an executor for the plan."""
        return PlanExecutor(self.llm, self.tool_registry)


class PlanExecutor:
    """Executes planned steps."""
    
    def __init__(self, llm, tool_registry):
        self.llm = llm
        self.tool_registry = tool_registry
    
    async def execute_step(self, step: ExecutionStep, context: dict) -> ExecutionStep:
        """Execute a single step."""
        step.status = StepStatus.RUNNING
        
        tool_name = step.action
        parameters = step.parameters
        
        # Interpolate parameters from context
        parameters = self._interpolate_parameters(parameters, context)
        
        # Execute tool
        result = await self.tool_registry.execute(tool_name, parameters)
        
        if result.success:
            step.status = StepStatus.COMPLETED
            step.result = result.data
            step.confidence = 1.0
        else:
            step.status = StepStatus.FAILED
            step.error = result.error
            
            # Retry if allowed
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                step.status = StepStatus.PENDING
                logger.warning(f"Retrying step {step.id} (attempt {step.retry_count})")
        
        step.metadata["execution_time"] = result.execution_time
        return step
    
    def _interpolate_parameters(self, parameters: dict, context: dict) -> dict:
        """Interpolate parameter values from context."""
        interpolated = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and "{{" in value:
                # Simple template interpolation
                for context_key, context_value in context.items():
                    placeholder = f"{{{{{context_key}}}}}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(context_value))
            
            # Recursively process nested dicts
            if isinstance(value, dict):
                value = self._interpolate_parameters(value, context)
            
            interpolated[key] = value
        
        return interpolated
    
    async def execute_plan(self, plan: ExecutionPlan, context: dict) -> ExecutionResult:
        """Execute a complete plan."""
        results = []
        tools_used = []
        
        # Build dependency graph
        step_map = {step.id: step for step in plan.steps}
        completed = set()
        
        while len(completed) < len(plan.steps):
            # Find steps with satisfied dependencies
            ready_steps = [
                step for step in plan.steps
                if step.id not in completed
                and all(dep in completed for dep in step.depends_on)
            ]
            
            if not ready_steps:
                break
            
            # Execute ready steps
            for step in ready_steps:
                result_step = await self.execute_step(step, context)
                results.append(result_step)
                
                if result_step.tool_name:
                    tools_used.append(result_step.tool_name)
                
                if result_step.status == StepStatus.COMPLETED:
                    completed.add(step.id)
                elif result_step.status == StepStatus.FAILED:
                    if result_step.requires_human_input:
                        return ExecutionResult(
                            success=False,
                            steps_executed=len(results),
                            tools_used=tools_used,
                            confidence=0.0,
                            error="Human input required",
                            requires_human_input=True,
                            human_prompt=result_step.human_prompt
                        )
                    # If retries exhausted, fail
                    if step.retry_count >= step.max_retries:
                        return ExecutionResult(
                            success=False,
                            steps_executed=len(results),
                            tools_used=tools_used,
                            confidence=0.0,
                            error=f"Step failed: {result_step.error}"
                        )
        
        # Check overall success
        all_completed = all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) 
            for s in plan.steps
        )
        
        successful = [r for r in results if r.status == StepStatus.COMPLETED]
        
        return ExecutionResult(
            success=all_completed,
            data=[r.result for r in successful],
            steps_executed=len(results),
            tools_used=list(set(tools_used)),
            confidence=sum(r.confidence for r in results) / len(results) if results else 0.0
        )
