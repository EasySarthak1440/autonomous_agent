"""
Workflow Execution Engine
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.agent import AutonomousAgent
from memory import MemorySystem
from .workflow import WorkflowStorage
from .workflow import Workflow, WorkflowAction, WorkflowTrigger, ActionType, TriggerType

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""
    pass


class WorkflowExecutor:
    """Executes workflows with support for conditionals, loops, and parallel execution."""
    
    def __init__(self, agent: AutonomousAgent, memory_system: MemorySystem):
        self.agent = agent
        self.memory = memory_system
        self.workflow_storage = WorkflowStorage(memory_system)
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        
    async def execute_workflow(self, workflow_id: str, 
                             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a workflow by ID."""
        workflow = await self.workflow_storage.load_workflow(workflow_id)
        if not workflow:
            raise WorkflowExecutionError(f"Workflow not found: {workflow_id}")
        
        if workflow.status != WorkflowStatus.ACTIVE:
            raise WorkflowExecutionError(f"Workflow is not active: {workflow.status.value}")
        
        execution_id = f"exec_{workflow_id}_{datetime.now().timestamp()}"
        logger.info(f"Starting workflow execution: {execution_id}")
        
        # Initialize execution context
        exec_context = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "start_time": datetime.now().isoformat(),
            "variables": context or {},
            "action_results": {}
        }
        
        self.active_executions[execution_id] = {
            "workflow": workflow,
            "context": exec_context,
            "status": "running",
            "current_action": None
        }
        
        try:
            # Find starting action (first action or trigger-defined start)
            start_action = self._find_start_action(workflow)
            if not start_action:
                raise WorkflowExecutionError("No starting action found in workflow")
            
            # Execute the workflow
            result = await self._execute_action_chain(start_action, exec_context)
            
            # Update execution status
            exec_context["end_time"] = datetime.now().isoformat()
            exec_context["result"] = result
            exec_context["status"] = "completed"
            
            self.active_executions[execution_id]["status"] = "completed"
            self.active_executions[execution_id]["result"] = result
            
            logger.info(f"Workflow execution completed: {execution_id}")
            return {
                "execution_id": execution_id,
                "status": "completed",
                "result": result,
                "context": exec_context
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {execution_id} - {e}")
            exec_context["end_time"] = datetime.now().isoformat()
            exec_context["error"] = str(e)
            exec_context["status"] = "failed"
            
            self.active_executions[execution_id]["status"] = "failed"
            self.active_executions[execution_id]["error"] = str(e)
            
            raise WorkflowExecutionError(f"Workflow execution failed: {e}")
    
    def _find_start_action(self, workflow: Workflow) -> Optional[WorkflowAction]:
        """Find the starting action for a workflow."""
        # For now, return the first action if no complex trigger logic
        if workflow.actions:
            return workflow.actions[0]
        return None
    
    async def _execute_action_chain(self, action: WorkflowAction, 
                                  context: Dict[str, Any]) -> Any:
        """Execute a chain of actions starting from the given action."""
        visited_actions = set()  # Prevent infinite loops
        current_action = action
        results = []
        
        while current_action and current_action.id not in visited_actions:
            visited_actions.add(current_action.id)
            logger.info(f"Executing action: {current_action.name} ({current_action.id})")
            
            # Update current action in context
            context["current_action"] = current_action.id
            
            # Execute the action
            action_result = await self._execute_action(current_action, context)
            results.append({
                "action_id": current_action.id,
                "action_name": current_action.name,
                "result": action_result,
                "status": "completed"
            })
            
            # Store result in context for future actions
            context["action_results"][current_action.id] = action_result
            
            # Determine next action
            next_action = self._get_next_action(current_action, action_result, workflow)
            current_action = next_action
        
        if current_action and current_action.id in visited_actions:
            logger.warning("Detected potential infinite loop in workflow execution")
        
        return {
            "executed_actions": results,
            "final_context": context
        }
    
    def _get_next_action(self, action: WorkflowAction, 
                        action_result: Any, 
                        workflow: Workflow) -> Optional[WorkflowAction]:
        """Determine the next action based on action result and workflow definition."""
        # Handle conditional branching
        if action.action_type == ActionType.CONDITION:
            condition_result = self._evaluate_condition(action.condition_expression, 
                                                      {"result": action_result, **context.get("variables", {})})
            if condition_result:
                next_action_id = action.condition_true_next
            else:
                next_action_id = action.condition_false_next
        else:
            next_action_id = action.next_action_id
        
        # Find the next action by ID
        if next_action_id:
            for next_action in workflow.actions:
                if next_action.id == next_action_id:
                    return next_action
        
        return None  # End of chain
    
    async def _execute_action(self, action: WorkflowAction, 
                            context: Dict[str, Any]) -> Any:
        """Execute a single action."""
        logger.info(f"Executing action type: {action.action_type}")
        
        if action.action_type == ActionType.TOOL_EXECUTION:
            return await self._execute_tool_action(action, context)
        elif action.action_type == ActionType.CONDITION:
            return await self._execute_condition_action(action, context)
        elif action.action_type == ActionType.DELAY:
            return await self._execute_delay_action(action, context)
        elif action.action_type == ActionType.PARALLEL:
            return await self._execute_parallel_action(action, context)
        else:
            raise WorkflowExecutionError(f"Unsupported action type: {action.action_type}")
    
    async def _execute_tool_action(self, action: WorkflowAction, 
                                 context: Dict[str, Any]) -> Any:
        """Execute a tool action."""
        if not action.tool_name:
            raise WorkflowExecutionError(f"No tool specified for action: {action.name}")
        
        # Prepare tool parameters with variable substitution
        parameters = self._substitute_variables(action.tool_parameters, context)
        
        logger.info(f"Executing tool: {action.tool_name} with parameters: {parameters}")
        
        # Execute the tool via the agent's tool registry
        result = await self.agent.tool_registry.execute(action.tool_name, parameters)
        
        if not result.success:
            raise WorkflowExecutionError(f"Tool execution failed: {result.error}")
        
        return result.data
    
    async def _execute_condition_action(self, action: WorkflowAction, 
                                      context: Dict[str, Any]) -> bool:
        """Execute a condition action."""
        if not action.condition_expression:
            raise WorkflowExecutionError(f"No condition expression for action: {action.name}")
        
        # Prepare context for condition evaluation
        condition_context = {
            "variables": context.get("variables", {}),
            "action_results": context.get("action_results", {}),
            "workflow_id": context.get("workflow_id"),
            "execution_id": context.get("execution_id")
        }
        
        result = self._evaluate_condition(action.condition_expression, condition_context)
        logger.info(f"Condition evaluated to: {result}")
        return result
    
    async def _execute_delay_action(self, action: WorkflowAction, 
                                  context: Dict[str, Any]) -> None:
        """Execute a delay action."""
        delay_seconds = action.delay_seconds or 1
        logger.info(f"Delaying for {delay_seconds} seconds")
        await asyncio.sleep(delay_seconds)
        return {"delayed_seconds": delay_seconds}
    
    async def _execute_parallel_action(self, action: WorkflowAction, 
                                     context: Dict[str, Any]) -> List[Any]:
        """Execute parallel actions."""
        if not action.parallel_actions:
            return []
        
        logger.info(f"Executing {len(action.parallel_actions)} parallel actions")
        
        # Execute all parallel actions concurrently
        tasks = [
            self._execute_action_chain(parallel_action, context.copy())
            for parallel_action in action.parallel_actions
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Parallel action {i} failed: {result}")
                processed_results.append({"error": str(result), "action_index": i})
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _substitute_variables(self, parameters: Dict[str, Any], 
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute variables in parameters using context."""
        # Simple variable substitution: {{variable_name}}
        parameters_str = json.dumps(parameters)
        
        # Replace workflow variables
        variables = context.get("variables", {})
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            parameters_str = parameters_str.replace(placeholder, json.dumps(var_value))
        
        # Replace action results
        action_results = context.get("action_results", {})
        for action_id, result in action_results.items():
            placeholder = f"{{{{action_result.{action_id}}}}}"
            parameters_str = parameters_str.replace(placeholder, json.dumps(result))
        
        return json.loads(parameters_str)
    
    def _evaluate_condition(self, expression: str, 
                          context: Dict[str, Any]) -> bool:
        """Evaluate a condition expression safely."""
        try:
            # Create a safe evaluation environment
            safe_context = {
                "__builtins__": {
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "True": True,
                    "False": False,
                    "None": None
                },
                **context
            }
            
            # Compile and evaluate the expression
            compiled_expr = compile(expression, "<condition>", "eval")
            result = eval(compiled_expr, safe_context)
            
            # Ensure we return a boolean
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {expression} - {e}")
            return False  # Fail safe
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow execution."""
        return self.active_executions.get(execution_id)
    
    def list_active_executions(self) -> List[Dict[str, Any]]:
        """List all active workflow executions."""
        return [
            {
                "execution_id": exec_id,
                "workflow_id": exec_data["workflow"].id,
                "workflow_name": exec_data["workflow"].name,
                "status": exec_data["status"],
                "start_time": exec_data["context"].get("start_time")
            }
            for exec_id, exec_data in self.active_executions.items()
        ]


# Global workflow executor instance (will be initialized in main)
workflow_executor: Optional[WorkflowExecutor] = None