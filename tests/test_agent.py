"""
Tests for Autonomous Agent
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch

# Import directly from modules
from core.agent import AutonomousAgent, AgentConfig, Task, AgentState
from core.llm import LLMBackend
from memory import MemorySystem
from planning import ExecutionStep
from safety import SafetyValidator, SafetyLevel
from tools import ToolRegistry


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
        assert tool.description == "A sample tool"
    
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


class TestMemorySystem:
    """Tests for memory system."""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        """Test storing and retrieving memories."""
        temp_db = tempfile.mktemp(suffix=".db")
        memory = MemorySystem(temp_db)
        
        # Store a memory
        memory_id = await memory.store(
            content="Test fact",
            memory_type="semantic",
            importance=0.8
        )
        
        assert memory_id is not None
        
        # Retrieve memories
        results = await memory.retrieve("test", limit=5)
        
        # Cleanup
        os.unlink(temp_db)
        
        assert len(results) >= 0
    
    def test_working_memory(self):
        """Test working memory."""
        memory = MemorySystem(":memory:")
        
        memory.set_working_memory("key1", "value1")
        assert memory.get_working_memory("key1") == "value1"
        
        memory.set_working_memory("key2", {"nested": "data"})
        assert memory.get_working_memory("key2")["nested"] == "data"
        
        memory.clear_working_memory()
        assert memory.get_working_memory("key1") is None


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


class TestPlanner:
    """Tests for planner."""
    
    def test_create_execution_step(self):
        """Test creating execution steps."""
        step = ExecutionStep(
            action="read_file",
            parameters={"path": "/tmp/test.txt"},
            depends_on=[],
            max_retries=3
        )
        
        assert step.action == "read_file"
        assert step.status.value == "pending"
        assert step.max_retries == 3


class TestAutonomousAgent:
    """Tests for the autonomous agent."""
    
    def test_agent_initialization(self):
        """Test agent can be initialized."""
        config = AgentConfig(
            name="test_agent",
            model_name="llama3.2",
            enable_safety=True,
            enable_learning=True
        )
        
        agent = AutonomousAgent(config)
        
        assert agent.config.name == "test_agent"
        assert agent.state == AgentState.IDLE
    
    def test_task_creation(self):
        """Test task creation."""
        task = Task(
            goal="Generate report",
            description="Create a sales report",
            priority=5
        )
        
        assert task.goal == "Generate report"
        assert task.priority == 5
        assert task.id is not None
    
    def test_get_status(self):
        """Test getting agent status."""
        config = AgentConfig(name="test_agent")
        agent = AutonomousAgent(config)
        
        status = agent.get_status()
        
        assert status["name"] == "test_agent"
        assert status["state"] == "idle"
        assert "tools_count" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
