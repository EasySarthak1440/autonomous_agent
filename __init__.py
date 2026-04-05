"""
Autonomous Agent for Business Process Automation
Self-contained AI system powered by LLMs.
"""

from .core import (
    AutonomousAgent,
    AgentConfig,
    AgentResponse,
    AgentState,
    Task,
)
from .llm import LLMBackend
from .memory import MemorySystem
from .planning import Planner, ExecutionPlan, ExecutionResult
from .tools import ToolRegistry, tool

__version__ = "1.0.0"

__all__ = [
    # Core
    "AutonomousAgent",
    "AgentConfig",
    "AgentResponse",
    "AgentState",
    "Task",
    # LLM
    "LLMBackend",
    # Memory
    "MemorySystem",
    # Planning
    "Planner",
    "ExecutionPlan",
    "ExecutionResult",
    # Tools
    "ToolRegistry",
    "tool",
]
