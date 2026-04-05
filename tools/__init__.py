"""
Tool Registry - Plugin architecture for agent tools
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a tool available to the agent."""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    function: Optional[Callable] = None
    category: str = "general"
    requires_approval: bool = False
    read_only: bool = False
    tags: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    tool_name: str = ""
    execution_time: float = 0.0
    metadata: dict = field(default_factory=dict)


class ToolRegistry:
    """
    Registry for managing agent tools.
    
    Provides:
    - Tool registration and discovery
    - Parameter validation
    - Execution with error handling
    - Tool documentation generation
    """
    
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._execution_history: list[ToolResult] = []
        
        # Register built-in tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """Register basic built-in tools."""
        try:
            from . import builtin
            from inspect import signature
            
            # Register all tools from the builtin module
            for tool_name in dir(builtin):
                if tool_name.startswith('_'):
                    continue
                obj = getattr(builtin, tool_name)
                if callable(obj) and hasattr(obj, '_is_tool'):
                    tool_def = getattr(obj, '_tool_definition', None)
                    if tool_def:
                        self.register(
                            name=tool_def.name,
                            func=obj,
                            description=tool_def.description,
                            parameters=tool_def.parameters
                        )
        except ImportError as e:
            logger.warning(f"Could not register builtin tools: {e}")
    
    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: Optional[dict] = None,
        category: str = "general",
        requires_approval: bool = False,
        read_only: bool = False,
        tags: Optional[list] = None
    ):
        """Register a tool with the registry."""
        import inspect
        
        # Get parameters from function signature if not provided
        if parameters is None:
            sig = inspect.signature(func)
            parameters = {
                param_name: {
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any",
                    "required": param.default == inspect.Parameter.empty,
                    "default": param.default if param.default != inspect.Parameter.empty else None
                }
                for param_name, param in sig.parameters.items()
            }
        
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            function=func,
            category=category,
            requires_approval=requires_approval,
            read_only=read_only,
            tags=tags or []
        )
        
        self._tools[name] = tool_def
        logger.info(f"Registered tool: {name}")
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all(self) -> dict[str, ToolDefinition]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_available_tools(self) -> list[dict]:
        """Get list of available tools with documentation."""
        return [
            {
                "name": name,
                "description": tool.description,
                "parameters": tool.parameters,
                "category": tool.category,
                "requires_approval": tool.requires_approval,
                "read_only": tool.read_only,
                "tags": tool.tags
            }
            for name, tool in self._tools.items()
        ]
    
    def get_by_category(self, category: str) -> list[ToolDefinition]:
        """Get tools by category."""
        return [t for t in self._tools.values() if t.category == category]
    
    def search(self, query: str) -> list[ToolDefinition]:
        """Search tools by name or description."""
        query = query.lower()
        return [
            tool for tool in self._tools.values()
            if query in tool.name.lower() or query in tool.description.lower()
        ]
    
    async def execute(
        self,
        name: str,
        parameters: dict,
        validate: bool = True
    ) -> ToolResult:
        """Execute a tool with given parameters."""
        import time
        start_time = time.time()
        
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {name}",
                tool_name=name
            )
        
        # Validate parameters
        if validate:
            validation_error = self._validate_parameters(tool, parameters)
            if validation_error:
                return ToolResult(
                    success=False,
                    error=validation_error,
                    tool_name=name
                )
        
        # Execute tool
        try:
            import asyncio
            if asyncio.iscoroutinefunction(tool.function):
                data = await tool.function(**parameters)
            else:
                data = tool.function(**parameters)
            
            execution_time = time.time() - start_time
            
            result = ToolResult(
                success=True,
                data=data,
                tool_name=name,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool execution failed: {name} - {e}")
            result = ToolResult(
                success=False,
                error=str(e),
                tool_name=name,
                execution_time=execution_time
            )
        
        self._execution_history.append(result)
        return result
    
    def _validate_parameters(self, tool: ToolDefinition, parameters: dict) -> Optional[str]:
        """Validate parameters against tool schema."""
        required_params = {
            name: spec 
            for name, spec in tool.parameters.items() 
            if spec.get("required", False)
        }
        
        # Check required parameters
        missing = [name for name in required_params if name not in parameters]
        if missing:
            return f"Missing required parameters: {', '.join(missing)}"
        
        # Check for unknown parameters
        unknown = [name for name in parameters if name not in tool.parameters]
        if unknown:
            return f"Unknown parameters: {', '.join(unknown)}"
        
        return None
    
    def get_execution_history(self, limit: int = 100) -> list[ToolResult]:
        """Get tool execution history."""
        return self._execution_history[-limit:]
    
    def clear_history(self):
        """Clear execution history."""
        self._execution_history = []


# Decorator for defining tools
def tool(
    name: str,
    description: str = "",
    parameters: Optional[dict] = None,
    category: str = "general",
    requires_approval: bool = False,
    read_only: bool = False,
    tags: Optional[list] = None
):
    """Decorator to define a tool."""
    def decorator(func: Callable) -> Callable:
        # Attach metadata to function
        func._is_tool = True
        func._tool_definition = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters or {},
            category=category,
            requires_approval=requires_approval,
            read_only=read_only,
            tags=tags or []
        )
        return func
    return decorator
