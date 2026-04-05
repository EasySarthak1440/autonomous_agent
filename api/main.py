"""
Autonomous Agent API - FastAPI REST endpoints
"""

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.agent import AutonomousAgent, AgentConfig, AgentResponse, AgentState, Task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: AutonomousAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global agent
    
    # Initialize agent with environment variables
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = os.environ.get("MODEL_NAME", "llama3.2")
    
    logger.info(f"Connecting to LLM at: {ollama_url} with model: {model_name}")
    
    config = AgentConfig(
        name="business_automation_agent",
        model_name=model_name,
        model_url=ollama_url,
        enable_safety=True,
        enable_learning=True,
        verbose=True
    )
    agent = AutonomousAgent(config)
    
    logger.info("Autonomous Agent started")
    
    yield
    
    # Cleanup on shutdown
    await agent.llm.close()
    logger.info("Autonomous Agent stopped")


app = FastAPI(
    title="Autonomous AI Agent API",
    description="Self-contained AI system for business process automation",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Request/Response Models ====================

class ExecuteTaskRequest(BaseModel):
    """Request to execute a task."""
    goal: str = Field(..., description="The goal to achieve")
    description: str = Field("", description="Detailed description")
    context: dict = Field(default_factory=dict, description="Additional context")
    priority: int = Field(1, ge=1, le=10, description="Task priority")
    
    class Config:
        json_schema_extra = {
            "example": {
                "goal": "Generate a sales report for Q1 2024",
                "description": "Create a comprehensive sales report",
                "context": {"department": "sales", "format": "pdf"},
                "priority": 5
            }
        }


class ExecuteTaskResponse(BaseModel):
    """Response from task execution."""
    task_id: str
    state: str
    result: dict = None
    error: str = None
    steps_executed: int
    tools_used: list
    execution_time: float
    confidence: float
    needs_human_input: bool = False


class ToolDefinition(BaseModel):
    """Tool definition."""
    name: str
    description: str
    parameters: dict
    category: str
    requires_approval: bool
    read_only: bool


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    agent: dict
    llm_available: bool
    tools_count: int
    memory_stats: dict


# ==================== API Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Autonomous AI Agent",
        "version": "1.0.0",
        "description": "Self-contained AI system for business process automation"
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check endpoint."""
    global agent
    
    llm_available = await agent.llm.check_health()
    tools = agent.tool_registry.get_available_tools()
    memory_stats = await agent.memory.get_statistics()
    
    return HealthResponse(
        status="healthy" if llm_available else "degraded",
        agent=agent.get_status(),
        llm_available=llm_available,
        tools_count=len(tools),
        memory_stats=memory_stats
    )


@app.post("/execute", response_model=ExecuteTaskResponse, tags=["Agent"])
async def execute_task(request: ExecuteTaskRequest, background_tasks: BackgroundTasks = None):
    """
    Execute a task autonomously.
    
    The agent will:
    1. Analyze the task and retrieve relevant context
    2. Create an execution plan using LLM reasoning
    3. Execute the plan with safety validation
    4. Learn from the execution for future improvement
    """
    global agent
    
    try:
        task = Task(
            description=request.description,
            goal=request.goal,
            context=request.context,
            priority=request.priority
        )
        
        response = await agent.execute(task)
        
        return ExecuteTaskResponse(
            task_id=response.task_id,
            state=response.state.value,
            result=response.result,
            error=response.error,
            steps_executed=response.steps_executed,
            tools_used=response.tools_used,
            execution_time=response.execution_time,
            confidence=response.confidence,
            needs_human_input=response.needs_human_input
        )
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools", response_model=list[ToolDefinition], tags=["Tools"])
async def list_tools(category: str = None):
    """List available tools."""
    global agent
    
    if category:
        tools = agent.tool_registry.get_by_category(category)
    else:
        tools = agent.tool_registry.get_all().values()
    
    return [
        ToolDefinition(
            name=t.name,
            description=t.description,
            parameters=t.parameters,
            category=t.category,
            requires_approval=t.requires_approval,
            read_only=t.read_only
        )
        for t in tools
    ]


@app.get("/tools/{tool_name}", response_model=ToolDefinition, tags=["Tools"])
async def get_tool(tool_name: str):
    """Get details of a specific tool."""
    global agent
    
    tool = agent.tool_registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    return ToolDefinition(
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        category=tool.category,
        requires_approval=tool.requires_approval,
        read_only=tool.read_only
    )


@app.post("/tools/{tool_name}/execute", tags=["Tools"])
async def execute_tool(tool_name: str, parameters: dict):
    """Execute a specific tool directly."""
    global agent
    
    result = await agent.tool_registry.execute(tool_name, parameters)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {
        "success": True,
        "tool": tool_name,
        "result": result.data,
        "execution_time": result.execution_time
    }


@app.get("/memory", tags=["Memory"])
async def get_memory(type: str = None, limit: int = 10):
    """Get memories."""
    global agent
    
    memories = await agent.memory.retrieve("", memory_type=type, limit=limit)
    return {"memories": memories}


@app.post("/memory", tags=["Memory"])
async def store_memory(content: str, memory_type: str = "semantic", importance: float = 0.5):
    """Store a memory."""
    global agent
    
    memory_id = await agent.memory.store(content, memory_type, importance)
    return {"success": True, "memory_id": memory_id}


@app.get("/memory/statistics", tags=["Memory"])
async def get_memory_stats():
    """Get memory statistics."""
    global agent
    
    return await agent.memory.get_statistics()


@app.get("/audit", tags=["Safety"])
async def get_audit_log(limit: int = 100):
    """Get safety audit log."""
    global agent
    
    if agent.safety:
        return {"audit_log": agent.safety.get_audit_log(limit)}
    return {"audit_log": []}


@app.get("/audit/statistics", tags=["Safety"])
async def get_safety_stats():
    """Get safety statistics."""
    global agent
    
    if agent.safety:
        return agent.safety.get_statistics()
    return {"error": "Safety not enabled"}


@app.post("/circuit-breaker/reset", tags=["Safety"])
async def reset_circuit_breaker():
    """Reset the circuit breaker."""
    global agent
    
    if agent.safety:
        agent.safety.reset_circuit_breaker()
        return {"success": True, "message": "Circuit breaker reset"}
    return {"error": "Safety not enabled"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
