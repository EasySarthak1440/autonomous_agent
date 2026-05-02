"""
Autonomous Agent for Business Process Automation
Self-contained AI system powered by LLMs.
"""

from .core.agent import AutonomousAgent, AgentConfig, AgentResponse, AgentState, Task
from .core.llm import LLMBackend
from .memory import MemorySystem
from .planning import Planner, ExecutionPlan, ExecutionResult
from .tools import ToolRegistry, tool

__version__ = "1.0.0"

__all__ = [
    "AutonomousAgent",
    "AgentConfig",
    "AgentResponse",
    "AgentState",
    "Task",
    "LLMBackend",
    "MemorySystem",
    "Planner",
    "ExecutionPlan",
    "ExecutionResult",
    "ToolRegistry",
    "tool",
]
