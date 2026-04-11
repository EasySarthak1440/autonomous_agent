"""
Workflow Automation System - Definitions and Storage
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from memory import MemorySystem

class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TriggerType(Enum):
    SCHEDULED = "scheduled"
    EVENT_BASED = "event_based"
    MANUAL = "manual"
    WEBHOOK = "webhook"


class ActionType(Enum):
    TOOL_EXECUTION = "tool_execution"
    CONDITION = "condition"
    DELAY = "delay"
    PARALLEL = "parallel"


@dataclass
class WorkflowTrigger:
    """Defines when a workflow should start."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trigger_type: TriggerType = TriggerType.MANUAL
    schedule: Optional[str] = None  # Cron expression for scheduled triggers
    event_name: Optional[str] = None  # For event-based triggers
    webhook_path: Optional[str] = None  # For webhook triggers
    conditions: Dict[str, Any] = field(default_factory=dict)  # Additional conditions
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowAction:
    """Defines an action to be executed in a workflow."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType = ActionType.TOOL_EXECUTION
    name: str = ""
    description: str = ""
    
    # For tool execution
    tool_name: Optional[str] = None
    tool_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # For conditions
    condition_expression: Optional[str] = None  # Python expression to evaluate
    
    # For delays
    delay_seconds: Optional[int] = None
    
    # For parallel execution
    parallel_actions: List['WorkflowAction'] = field(default_factory=list)
    
    # Control flow
    next_action_id: Optional[str] = None
    condition_true_next: Optional[str] = None  # For conditional branching
    condition_false_next: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.DRAFT
    
    trigger: WorkflowTrigger = field(default_factory=WorkflowTrigger)
    actions: List[WorkflowAction] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowStorage:
    """Handles persistence and retrieval of workflow definitions."""
    
    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
    
    async def save_workflow(self, workflow: Workflow) -> str:
        """Save a workflow definition."""
        workflow.updated_at = datetime.now()
        
        # Convert workflow to storable format
        workflow_data = {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "status": workflow.status.value,
            "trigger": {
                "id": workflow.trigger.id,
                "trigger_type": workflow.trigger.trigger_type.value,
                "schedule": workflow.trigger.schedule,
                "event_name": workflow.trigger.event_name,
                "webhook_path": workflow.trigger.webhook_path,
                "conditions": workflow.trigger.conditions,
                "metadata": workflow.trigger.metadata
            },
            "actions": [
                {
                    "id": action.id,
                    "action_type": action.action_type.value,
                    "name": action.name,
                    "description": action.description,
                    "tool_name": action.tool_name,
                    "tool_parameters": action.tool_parameters,
                    "condition_expression": action.condition_expression,
                    "delay_seconds": action.delay_seconds,
                    "parallel_actions": [self._action_to_dict(a) for a in action.parallel_actions],
                    "next_action_id": action.next_action_id,
                    "condition_true_next": action.condition_true_next,
                    "condition_false_next": action.condition_false_next,
                    "metadata": action.metadata
                }
                for action in workflow.actions
            ],
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "created_by": workflow.created_by,
            "tags": workflow.tags,
            "metadata": workflow.metadata
        }
        
        # Store in semantic memory
        memory_id = await self.memory.store_knowledge(
            f"Workflow: {workflow.name} - {workflow.description}",
            importance=0.8,
            metadata={
                "workflow_data": workflow_data,
                "workflow_id": workflow.id,
                "type": "workflow_definition"
            }
        )
        
        return memory_id
    
    async def load_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Load a workflow definition by ID."""
        # Search for workflow in memory
        results = await self.memory.retrieve(
            f"workflow_id:{workflow_id}",
            memory_type="semantic",
            limit=1
        )
        
        if not results:
            return None
        
        # Extract workflow data from metadata
        metadata = results[0].get("metadata", {})
        workflow_data = metadata.get("workflow_data")
        
        if not workflow_data:
            return None
        
        return self._dict_to_workflow(workflow_data)
    
    async def list_workflows(self, status: Optional[WorkflowStatus] = None, 
                           tags: Optional[List[str]] = None) -> List[Workflow]:
        """List workflows with optional filtering."""
        # Search for all workflow definitions
        results = await self.memory.retrieve(
            "type:workflow_definition",
            memory_type="semantic",
            limit=100
        )
        
        workflows = []
        for result in results:
            metadata = result.get("metadata", {})
            workflow_data = metadata.get("workflow_data")
            
            if workflow_data:
                workflow = self._dict_to_workflow(workflow_data)
                
                # Apply filters
                if status and workflow.status != status:
                    continue
                if tags and not any(tag in workflow.tags for tag in tags):
                    continue
                
                workflows.append(workflow)
        
        return workflows
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow definition."""
        # Note: In a full implementation, we would delete from memory
        # For now, we'll mark as archived
        workflow = await self.load_workflow(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.ARCHIVED
            await self.save_workflow(workflow)
            return True
        return False
    
    def _action_to_dict(self, action: WorkflowAction) -> Dict[str, Any]:
        """Convert WorkflowAction to dictionary."""
        return {
            "id": action.id,
            "action_type": action.action_type.value,
            "name": action.name,
            "description": action.description,
            "tool_name": action.tool_name,
            "tool_parameters": action.tool_parameters,
            "condition_expression": action.condition_expression,
            "delay_seconds": action.delay_seconds,
            "parallel_actions": [self._action_to_dict(a) for a in action.parallel_actions],
            "next_action_id": action.next_action_id,
            "condition_true_next": action.condition_true_next,
            "condition_false_next": action.condition_false_next,
            "metadata": action.metadata
        }
    
    def _dict_to_workflow(self, data: Dict[str, Any]) -> Workflow:
        """Convert dictionary to Workflow object."""
        # Reconstruct trigger
        trigger_data = data.get("trigger", {})
        trigger = WorkflowTrigger(
            id=trigger_data.get("id", str(uuid.uuid4())),
            trigger_type=TriggerType(trigger_data.get("trigger_type", "manual")),
            schedule=trigger_data.get("schedule"),
            event_name=trigger_data.get("event_name"),
            webhook_path=trigger_data.get("webhook_path"),
            conditions=trigger_data.get("conditions", {}),
            metadata=trigger_data.get("metadata", {})
        )
        
        # Reconstruct actions
        actions = []
        for action_data in data.get("actions", []):
            action = self._dict_to_action(action_data)
            actions.append(action)
        
        # Create workflow
        workflow = Workflow(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            status=WorkflowStatus(data.get("status", "draft")),
            trigger=trigger,
            actions=actions,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
            created_by=data.get("created_by"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
        
        return workflow
    
    def _dict_to_action(self, data: Dict[str, Any]) -> WorkflowAction:
        """Convert dictionary to WorkflowAction."""
        # Reconstruct parallel actions
        parallel_actions = []
        for parallel_data in data.get("parallel_actions", []):
            parallel_action = self._dict_to_action(parallel_data)
            parallel_actions.append(parallel_action)
        
        action = WorkflowAction(
            id=data.get("id", str(uuid.uuid4())),
            action_type=ActionType(data.get("action_type", "tool_execution")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tool_name=data.get("tool_name"),
            tool_parameters=data.get("tool_parameters", {}),
            condition_expression=data.get("condition_expression"),
            delay_seconds=data.get("delay_seconds"),
            parallel_actions=parallel_actions,
            next_action_id=data.get("next_action_id"),
            condition_true_next=data.get("condition_true_next"),
            condition_false_next=data.get("condition_false_next"),
            metadata=data.get("metadata", {})
        )
        
        return action