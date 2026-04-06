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
    tool_name: str = ""
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
        
        # Find relevant tools by searching goal keywords
        relevant_tools = self.tool_registry.search(goal)
        if not relevant_tools:
            # If no matches, use all tools but with concise descriptions
            relevant_tools = list(self.tool_registry.get_all().values())
        
        # Build concise tool descriptions with parameters
        tools_list = []
        for t in relevant_tools:
            # Handle both dict and ToolDefinition
            if isinstance(t, dict):
                t_name = t.get("name", "")
                t_desc = t.get("description", "")
                t_params = t.get("parameters", {})
            else:
                t_name = t.name
                t_desc = t.description
                t_params = t.parameters
            
            params = []
            for pname, pspec in t_params.items():
                req = pspec.get("required", False)
                ptype = pspec.get("type", "any")
                params.append(f"{pname} ({ptype}, {'required' if req else 'optional'})")
            params_str = ", ".join(params) if params else "no params"
            tools_list.append(f'  "{t_name}": {t_desc}. Params: {params_str}')
        
        tools_description = "\n".join(tools_list)
        
        system_prompt = f"""You plan tasks by selecting tools. Return ONLY valid JSON.

Available tools:
{tools_description}

Rules:
- Use EXACT tool names from the list
- Include ALL required parameters with real values
- Return ONLY JSON, no markdown, no explanation"""
        
        user_prompt = f"""Goal: {goal}

Context: {json.dumps(context)}

Return JSON with steps. Each step has "action" (tool name) and "parameters" (dict with values)."""

        try:
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
            
            logger.info(f"LLM plan data: {json.dumps(plan_data, indent=2)}")
            
            steps = plan_data.get("steps", [])
            
            # Validate steps have real tool names
            valid_tool_names = {t["name"] for t in available_tools}
            valid_steps = [s for s in steps if s.get("action") in valid_tool_names]
            
            if not valid_steps:
                raise Exception(f"No valid tool steps found. Got: {steps}")
            
            plan = ExecutionPlan(
                goal=plan_data.get("goal", goal),
                estimated_duration=plan_data.get("estimated_duration", 0.0)
            )
            
            for step_data in valid_steps:
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
            return ExecutionPlan(
                goal=goal,
                steps=[ExecutionStep(action="generate_report", parameters={"title": goal, "data": {"goal": goal}})]
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
        """Execute a single step with retry logic."""
        step.status = StepStatus.RUNNING
        
        tool_name = step.action
        parameters = step.parameters
        
        # Interpolate parameters from context
        parameters = self._interpolate_parameters(parameters, context)
        
        logger.info(f"Executing step: {tool_name} with params: {parameters}")
        
        # Execute tool with retries
        result = None
        for attempt in range(step.max_retries + 1):
            step.retry_count = attempt
            result = await self.tool_registry.execute(tool_name, parameters)
            
            if result.success:
                logger.info(f"Step {tool_name} succeeded on attempt {attempt + 1}")
                break
            
            if attempt < step.max_retries:
                logger.warning(f"Step {tool_name} failed (attempt {attempt + 1}/{step.max_retries}): {result.error}")
        
        step.tool_name = tool_name
        
        if result and result.success:
            step.status = StepStatus.COMPLETED
            step.result = result.data
            step.confidence = 1.0
        else:
            step.status = StepStatus.FAILED
            step.error = result.error if result else "No result"
            step.confidence = 0.0
            logger.error(f"Step {tool_name} failed after retries: {step.error}")
        
        step.metadata["execution_time"] = result.execution_time if result else 0.0
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
