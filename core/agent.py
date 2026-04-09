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
from typing import Any, Callable, Dict, List, Optional
import time
import hashlib

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm import LLMBackend
from tools import ToolRegistry

logger = logging.getLogger(__name__)

# Constants for AI/ML guidelines
TOKEN_USAGE_THRESHOLD = 0.8  # Keep context under 80% of model limits
CONFIDENCE_THRESHOLD_DEFAULT = 0.7
SAFETY_CHECK_ENABLED = True
AUDIT_LOG_ENABLED = True
REASONING_TRACE_ENABLED = True

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


# AI/ML Specific Constants
DEFAULT_MAX_TOKENS = 4096
TOKEN_USAGE_WARNING_THRESHOLD = 0.8
TOKEN_USAGE_CRITICAL_THRESHOLD = 0.95
CONFIDENCE_THRESHOLD_DEFAULT = 0.7
HALLUCINATION_CHECK_ENABLED = True
REASONING_TRACE_ENABLED = True
FALLBACK_STRATEGY_ENABLED = True


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
    
    # Security & Safety Enhancements
    enable_harmful_content_filter: bool = True
    enable_hallucination_detection: bool = True
    enable_data_masking: bool = True
    max_tool_execution_time: int = 30  # seconds
    enable_audit_logging: bool = True
    enable_reasoning_trace: bool = True
    tool_allowlist: List[str] = field(default_factory=list)  # Empty means all tools allowed
    
    # Observability & Monitoring
    enable_structured_logging: bool = True
    enable_metrics_collection: bool = True
    enable_tracing: bool = True
    log_level: str = "INFO"
    metrics_port: Optional[int] = None
    
    # DevOps & Deployment
    model_version: str = "1.0.0"
    enable_canary_deployment: bool = False
    canary_percentage: int = 5
    
    # Testing & Validation
    require_human_approval_for_high_risk: bool = True
    high_risk_operations: List[str] = field(default_factory=lambda: ["data_deletion", "external_communication", "system_modification"])
    use_synthetic_test_data: bool = True


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
        Execute a task autonomously with AI/ML specific enhancements.
        
        Args:
            task: The task to execute
            
        Returns:
            AgentResponse with results and metadata
        """
        # Generate trace ID for observability
        trace_id = hashlib.md5(f"{task.id}{datetime.now()}".encode()).hexdigest()[:8]
        
        # Start timing for performance metrics
        start_time = time.time()
        self.current_task = task
        self.state = AgentState.THINKING
        
        # Initialize metrics
        metrics = {
            "trace_id": trace_id,
            "start_time": start_time,
            "llm_calls": 0,
            "tool_calls": 0,
            "safety_checks": 0,
            "hallucination_checks": 0,
            "tokens_used": 0,
            "context_truncated": False
        }
        
        try:
            # Step 1: Analyze task and retrieve relevant context with token management
            context = await self._prepare_context_with_token_management(task, metrics)
            
            # Step 2: Generate execution plan with fallback strategy
            plan = await self._generate_plan_with_fallback(task.goal, context, metrics)
            
            # Step 3: Execute plan with enhanced safety checks
            result = await self._execute_plan_with_enhanced_safety(plan, context, metrics)
            
            # Step 4: Learn from execution with validation
            if self.config.enable_learning:
                await self._learn_from_execution_with_validation(task, result, metrics)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            metrics["execution_time"] = execution_time
            
            # Validate output for hallucinations if enabled
            if self.config.enable_hallucination_detection and result.success:
                hallucination_score = await self._check_for_hallucinations(result.data, task.goal)
                metrics["hallucination_score"] = hallucination_score
                if hallucination_score > 0.7:  # High hallucination risk
                    logger.warning(f"High hallucination risk detected: {hallucination_score}")
                    # Optionally mark result as needing review
                    if hasattr(result, 'metadata'):
                        result.metadata["hallucination_risk"] = hallucination_score
            
            # Create enhanced response with metrics
            response = AgentResponse(
                task_id=task.id,
                state=AgentState.COMPLETED,
                result=result.data,
                steps_executed=result.steps_executed,
                tools_used=result.tools_used,
                execution_time=execution_time,
                confidence=result.confidence,
                metadata={
                    **(result.metadata if result.metadata else {}),
                    "metrics": metrics,
                    "trace_id": trace_id
                }
            )
            
            # Log structured metrics if enabled
            if self.config.enable_structured_logging:
                self._log_structured_metrics(task, response, metrics)
            
            # Collect metrics if enabled
            if self.config.enable_metrics_collection:
                await self._collect_metrics(task, response, metrics)
                
        except Exception as e:
            # Calculate execution time for failed tasks
            execution_time = time.time() - start_time
            
            logger.error(f"Task execution failed: {e}", exc_info=True)
            self.state = AgentState.ERROR
            
            # Create error response with metrics
            response = AgentResponse(
                task_id=task.id,
                state=AgentState.ERROR,
                error=str(e),
                execution_time=execution_time,
                metrics={
                    "trace_id": trace_id,
                    "execution_time": execution_time,
                    "error": str(e),
                    **metrics
                }
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

    async def _prepare_context_with_token_management(self, task: Task, metrics: Dict) -> dict:
        """Prepare execution context with token management."""
        # Prepare base context
        context = await self._prepare_context(task)
        
        # Estimate token usage (simplified estimation)
        context_str = json.dumps(context)
        estimated_tokens = len(context_str) // 4  # Rough approximation: 4 chars per token
        
        # Update metrics
        metrics["tokens_used"] = estimated_tokens
        metrics["estimated_context_tokens"] = estimated_tokens
        
        # Check if we're approaching token limits
        if estimated_tokens > (self.config.max_tokens * TOKEN_USAGE_WARNING_THRESHOLD):
            logger.warning(f"High token usage detected: {estimated_tokens} tokens")
            metrics["context_truncated"] = True
            
            # Truncate context if needed (simplified approach)
            if estimated_tokens > (self.config.max_tokens * TOKEN_USAGE_CRITICAL_THRESHOLD):
                # Keep only essential task information
                context = {
                    "task": context.get("task", {}),
                    "available_tools": context.get("available_tools", []),
                    "config": context.get("config", {})
                }
                metrics["context_truncated"] = True
                metrics["truncated_reason"] = "token_limit_exceeded"
        
        return context

    async def _generate_plan_with_fallback(self, goal: str, context: dict, metrics: Dict):
        """Generate execution plan with fallback strategy."""
        try:
            # Try primary planning approach
            plan = await self.planner.create_plan(goal, context)
            metrics["planning_approach"] = "primary"
            return plan
        except Exception as e:
            logger.warning(f"Primary planning failed, trying fallback: {e}")
            metrics["planning_approach"] = "fallback"
            metrics["planning_error"] = str(e)
            
            # Fallback: create a simple plan
            from planning import Plan
            plan = Plan(
                goal=goal,
                steps=[],  # Empty plan as fallback
                context=context
            )
            return plan

    async def _execute_plan_with_enhanced_safety(self, plan, context, metrics):
        """Execute plan with enhanced safety checks."""
        ExecutionResult = _get_execution_result()
        
        self.state = AgentState.EXECUTING
        executor = self.planner.create_executor()
        
        steps_executed = 0
        tools_used = []
        results = []
        
        for step in plan.steps:
            # Update tool call metrics
            metrics["tool_calls"] += 1
            
            # Safety check before each step
            if self.config.enable_safety and self.safety:
                metrics["safety_checks"] += 1
                is_safe = await self.safety.validate_action(step, context)
                if not is_safe:
                    logger.warning(f"Step blocked by safety: {step.action}")
                    metrics["blocked_steps"] = metrics.get("blocked_steps", 0) + 1
                    continue
            
            # Execute step with timeout
            try:
                # Apply timeout if configured
                timeout = self.config.max_tool_execution_time if hasattr(self.config, 'max_tool_execution_time') else 30
                result = await asyncio.wait_for(
                    executor.execute_step(step, context), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Step execution timed out after {timeout}s: {step.action}")
                ExecutionResult = _get_execution_result()
                return ExecutionResult(
                    data=None,
                    success=False,
                    steps_executed=steps_executed,
                    tools_used=tools_used,
                    confidence=0.0,
                    error=f"Step execution timed out after {timeout}s",
                    requires_human_input=False
                )
            except Exception as e:
                logger.error(f"Step execution failed: {e}")
                ExecutionResult = _get_execution_result()
                return ExecutionResult(
                    data=None,
                    success=False,
                    steps_executed=steps_executed,
                    tools_used=tools_used,
                    confidence=0.0,
                    error=str(e),
                    requires_human_input=False
                )
            
            steps_executed += 1
            
            if result.tool_name:
                tools_used.append(result.tool_name)
            
            results.append(result)
            
            # Check if we need human input for high-risk operations
            if result.requires_human_input:
                # Check if this is a high-risk operation requiring human approval
                if self.config.require_human_approval_for_high_risk:
                    # Check if step involves high-risk operation
                    step_action = getattr(step, 'action', '').lower()
                    is_high_risk = any(risk_op in step_action for risk_op in self.config.high_risk_operations)
                    
                    if is_high_risk:
                        logger.warning(f"High-risk operation requires human approval: {step_action}")
                        ExecutionResult = _get_execution_result()
                        return ExecutionResult(
                            data=None,
                            success=False,
                            steps_executed=steps_executed,
                            tools_used=tools_used,
                            confidence=0.0,
                            error="Human approval required for high-risk operation",
                            requires_human_input=True,
                            human_prompt=f"High-risk operation detected: {step_action}. Please approve to continue."
                        )
            
            # Check confidence - stop if too low
            if result.confidence < self.config.confidence_threshold:
                logger.warning(f"Low confidence: {result.confidence}")
                metrics["low_confidence_steps"] = metrics.get("low_confidence_steps", 0) + 1
        
        # Aggregate results
        final_result = self._aggregate_results(results)
        ExecutionResult = _get_execution_result()
        
        # Calculate average confidence
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0
        
        return ExecutionResult(
            data=final_result,
            success=True,
            steps_executed=steps_executed,
            tools_used=tools_used,
            confidence=avg_confidence,
            metadata={"plan_id": getattr(plan, 'id', None), "results": [r.metadata for r in results]}
        )

    async def _learn_from_execution_with_validation(self, task: Task, result, metrics: Dict):
        """Learn from execution with validation."""
        # Validate learning data before storing
        if not task.goal or not isinstance(task.goal, str):
            logger.warning("Invalid task goal for learning, skipping")
            return
        
        # Store experience in episodic memory
        await self.memory.store_experience(
            task=task.goal,
            outcome="success" if result.success else "failure",
            steps=result.metadata.get("results", []) if result.metadata else [],
            tools_used=result.tools_used if hasattr(result, 'tools_used') else [],
            confidence=result.confidence if hasattr(result, 'confidence') else 0.0
        )
        
        logger.info(f"Learned from execution: {task.goal} - {getattr(result, 'success', False)}")
        
        # Update learning metrics
        metrics["learning_updated"] = True
        metrics["learning_success"] = getattr(result, 'success', False)

    async def _check_for_hallucinations(self, data: Any, goal: str) -> float:
        """Check for potential hallucinations in LLM output.
        
        Returns:
            Hallucination score between 0.0 (no hallucination) and 1.0 (definite hallucination)
        """
        # This is a simplified implementation
        # In production, you would use more sophisticated techniques
        
        if not data or not goal:
            return 0.0
        
        # Convert data to string for analysis
        if isinstance(data, dict):
            data_str = json.dumps(data)
        elif isinstance(data, list):
            data_str = json.dumps(data)
        else:
            data_str = str(data)
        
        # Simple heuristic checks (would be replaced with proper models in production)
        hallucination_indicators = [
            # Check for overly confident or absolute statements without basis
            data_str.count("definitely") + data_str.count("absolutely") + data_str.count("certainly"),
            # Check for fabricated specifics (numbers, dates, names that seem too specific)
            len([c for c in data_str if c.isdigit()]) / max(len(data_str), 1) * 10,  # Density of digits
            # Check for vague references that might be made up
            data_str.count("according to") + data_str.count("studies show") + data_str.count("research indicates"),
        ]
        
        # Normalize score (simplified)
        raw_score = sum(hallucination_indicators) / max(len(data_str) / 100, 1)
        hallucination_score = min(raw_score / 10, 1.0)  # Cap at 1.0
        
        return hallucination_score

    def _log_structured_metrics(self, task: Task, response: AgentResponse, metrics: Dict):
        """Log structured metrics for observability."""
        if not self.config.enable_structured_logging:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": metrics.get("trace_id"),
            "task_id": task.id,
            "task_goal": task.goal[:100],  # Truncate for privacy
            "task_priority": task.priority,
            "agent_state": response.state.value,
            "execution_time": response.execution_time,
            "steps_executed": response.steps_executed,
            "tools_used": response.tools_used,
            "confidence": response.confidence,
            "llm_calls": metrics.get("llm_calls", 0),
            "tool_calls": metrics.get("tool_calls", 0),
            "safety_checks": metrics.get("safety_checks", 0),
            "tokens_used": metrics.get("tokens_used", 0),
            "context_truncated": metrics.get("context_truncated", False),
            "hallucination_score": metrics.get("hallucination_score", 0.0),
            "error": response.error if hasattr(response, 'error') and response.error else None
        }
        
        logger.info(f"STRUCTURED_METRICS: {json.dumps(log_entry)}")

    async def _collect_metrics(self, task: Task, response: AgentResponse, metrics: Dict):
        """Collect metrics for monitoring systems."""
        if not self.config.enable_metrics_collection:
            return
        
        # In a real implementation, this would send metrics to a monitoring system
        # For now, we'll just log them
        if self.config.metrics_port:
            # Example: send to a metrics server
            pass
        
        # Log key metrics
        logger.debug(f"METRICS_COLLECTED: trace_id={metrics.get('trace_id')}, "
                    f"execution_time={metrics.get('execution_time')}, "
                    f"tokens_used={metrics.get('tokens_used')}, "
                    f"tool_calls={metrics.get('tool_calls')}, "
                    f"confidence={response.confidence}")

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
