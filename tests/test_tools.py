"""
Tests for Tool Registry and Safety - standalone
"""

import pytest
import asyncio
import tempfile
import os
import sys
from tools import ToolRegistry, ToolDefinition
from safety import SafetyValidator, SafetyLevel
from planning import ExecutionStep

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestToolRegistry:
    """Tests for tool registry."""
    
    def test_register_tool(self):
        """Test tool registration."""
        registry = ToolRegistry()
        
        def sample_tool(param1: str, param2: int = 10) -> dict:
            return {"result": param1}
        
        registry.register(
            name="sample_tool",
            func=sample_tool,
            description="A sample tool",
            parameters={"param1": {"type": "string"}, "param2": {"type": "number"}}
        )
        
        tool = registry.get("sample_tool")
        assert tool is not None
        assert tool.name == "sample_tool"
    
    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution."""
        registry = ToolRegistry()
        
        def add_numbers(a: int, b: int) -> dict:
            return {"sum": a + b}
        
        registry.register("add", add_numbers, "Add two numbers")
        
        result = await registry.execute("add", {"a": 5, "b": 3})
        
        assert result.success is True
        assert result.data["sum"] == 8
    
    @pytest.mark.asyncio
    async def test_execute_invalid_tool(self):
        """Test executing non-existent tool."""
        registry = ToolRegistry()
        
        result = await registry.execute("nonexistent", {})
        
        assert result.success is False
        assert "not found" in result.error.lower()


class TestSafetyValidator:
    """Tests for safety validator."""
    
    @pytest.mark.asyncio
    async def test_validate_safe_action(self):
        """Test validation of safe action."""
        safety = SafetyValidator()
        
        step = ExecutionStep(action="read_file", parameters={"path": "/tmp/test.txt"})
        
        result = await safety.validate_action(step, {})
        
        assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_validate_dangerous_action(self):
        """Test blocking dangerous action."""
        safety = SafetyValidator()
        
        step = ExecutionStep(
            action="execute_command", 
            parameters={"command": "rm -rf /"}
        )
        
        result = await safety.validate_action(step, {})
        
        assert result.allowed is False
        assert result.safety_level == SafetyLevel.BLOCKED
    
    def test_audit_log(self):
        """Test audit logging."""
        safety = SafetyValidator()
        
        log = safety.get_audit_log()
        
        assert isinstance(log, list)
    
    def test_statistics(self):
        """Test safety statistics."""
        safety = SafetyValidator()
        
        stats = safety.get_statistics()
        
        assert "total_actions" in stats
        assert "rules_count" in stats
        assert stats["rules_count"] > 0


class TestExecutionStep:
    """Tests for execution steps."""
    
    def test_create_step(self):
        """Test creating execution steps."""
        step = ExecutionStep(
            action="read_file",
            parameters={"path": "/tmp/test.txt"},
            depends_on=[],
            max_retries=3
        )
        
        assert step.action == "read_file"
        assert step.max_retries == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
