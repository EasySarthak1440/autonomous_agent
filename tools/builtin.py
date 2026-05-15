"""
Built-in Tools for the Autonomous Agent
"""

import ast
import json
import logging
import math
import operator
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Optional

from . import tool

logger = logging.getLogger(__name__)


# ==================== Filesystem Tools ====================

@tool(
    name="read_file",
    description="Read contents of a file from the filesystem",
    category="filesystem",
    read_only=True,
    tags=["file", "read", "io"]
)
def read_file(path: str, encoding: str = "utf-8") -> dict:
    """Read a file and return its contents."""
    try:
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()
        return {
            "success": True,
            "path": path,
            "content": content,
            "size": len(content),
            "lines": len(content.splitlines())
        }
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Database Tools ====================

_SELECT_OPS = {"SELECT", "WITH"}
_WRITE_OPS = {"INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "TRUNCATE", "ALTER"}


def _detect_query_type(query: str) -> str:
    """Detect the SQL query type from the statement."""
    q = query.strip().upper()
    if q.startswith("SELECT") or q.startswith("WITH"):
        return "select"
    if q.startswith("INSERT"):
        return "insert"
    if q.startswith("UPDATE"):
        return "update"
    if q.startswith("DELETE"):
        return "delete"
    if q.startswith("CREATE DATABASE"):
        return "create_database"
    if q.startswith("CREATE TABLE"):
        return "create_table"
    if q.startswith("CREATE"):
        return "create"
    if q.startswith("DROP"):
        return "drop"
    if q.startswith("TRUNCATE"):
        return "truncate"
    if q.startswith("ALTER"):
        return "alter"
    if q.startswith("PRAGMA"):
        return "pragma"
    return "other"


def _query_result_to_dict(cursor) -> dict:
    """Convert cursor result to a dict with columns and rows."""
    rows = [dict(row) for row in cursor.fetchall()]
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return {"columns": columns, "rows": rows, "row_count": len(rows)}


@tool(
    name="sql_manager",
    description="Execute any SQL query on a SQLite database. "
                "Supports: CREATE TABLE, INSERT, SELECT, UPDATE, DELETE, "
                "DROP, TRUNCATE, JOIN, GROUP BY, ORDER BY, LIMIT, "
                "aggregate functions, subqueries, and more. "
                "Use params for safe parameterized queries.",
    category="database",
    tags=["database", "sql", "sqlite", "query", "manager"]
)
def sql_manager(db_path: str, query: str, params: list = None) -> dict:
    """
    Execute SQL queries on a SQLite database.

    Args:
        db_path: Path to the SQLite database file
        query: The SQL query to execute
        params: Optional list of parameters for parameterized queries (prevents SQL injection)

    Returns:
        dict with success status, operation type, and query results
    """
    if params is None:
        params = []

    if not query or not query.strip():
        return {"success": False, "error": "Query cannot be empty"}

    try:
        qtype = _detect_query_type(query)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(query, params)

        if qtype == "select":
            result = _query_result_to_dict(cursor)
            result.update({"success": True, "operation": "select"})
            conn.close()
            return result

        conn.commit()

        if qtype == "insert":
            result = {
                "success": True,
                "operation": "insert",
                "affected_rows": cursor.rowcount,
                "last_insert_id": cursor.lastrowid,
            }
        elif qtype == "update":
            result = {
                "success": True,
                "operation": "update",
                "affected_rows": cursor.rowcount,
            }
        elif qtype == "delete":
            result = {
                "success": True,
                "operation": "delete",
                "affected_rows": cursor.rowcount,
            }
        elif qtype == "create_database":
            result = {
                "success": True,
                "operation": "create_database",
                "message": f"Database ready: {db_path}",
            }
        elif qtype in ("create_table", "create"):
            result = {
                "success": True,
                "operation": qtype,
                "message": "Object created successfully",
            }
        elif qtype == "drop":
            result = {
                "success": True,
                "operation": "drop",
                "message": "Object dropped successfully",
            }
        elif qtype == "truncate":
            result = {
                "success": True,
                "operation": "truncate",
                "message": "Table truncated successfully",
            }
        else:
            result = {
                "success": True,
                "operation": qtype,
                "affected_rows": cursor.rowcount,
                "message": "Query executed successfully",
            }

        conn.close()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Data Processing Tools ====================

@tool(
    name="filter_data",
    description="Filter data based on conditions",
    category="data",
    read_only=True,
    tags=["data", "filter", "processing"]
)
def filter_data(data: list, condition: str) -> dict:
    """Filter list data using simple condition."""
    try:
        if '==' in condition:
            field, value = condition.split('==')
            filtered = [d for d in data if d.get(field.strip()) == value.strip()]
        elif '!=' in condition:
            field, value = condition.split('!=')
            filtered = [d for d in data if d.get(field.strip()) != value.strip()]
        elif '>' in condition:
            field, value = condition.split('>')
            filtered = [d for d in data if d.get(field.strip()) and d.get(field.strip()) > float(value)]
        elif '<' in condition:
            field, value = condition.split('<')
            filtered = [d for d in data if d.get(field.strip()) and d.get(field.strip()) < float(value)]
        else:
            filtered = data

        return {
            "success": True,
            "original_count": len(data),
            "filtered_count": len(filtered),
            "data": filtered
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.UAdd: operator.pos, ast.USub: operator.neg,
}

_SAFE_FUNCS = {
    "abs": abs, "round": round, "sqrt": math.sqrt,
    "floor": math.floor, "ceil": math.ceil,
    "min": min, "max": max, "sum": sum,
}

def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_safe_eval(elt) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(elt) for elt in node.elts)
    if isinstance(node, ast.BinOp):
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left)
        for cmp_op, comparator in zip(node.ops, node.comparators):
            right = _safe_eval(comparator)
            if isinstance(cmp_op, ast.Eq):
                result = left == right
            elif isinstance(cmp_op, ast.NotEq):
                result = left != right
            elif isinstance(cmp_op, ast.Lt):
                result = left < right
            elif isinstance(cmp_op, ast.LtE):
                result = left <= right
            elif isinstance(cmp_op, ast.Gt):
                result = left > right
            elif isinstance(cmp_op, ast.GtE):
                result = left >= right
            else:
                raise ValueError(f"Unsupported comparison: {ast.dump(cmp_op)}")
            if not result:
                return result
            left = right
        return True
    if isinstance(node, ast.Subscript):
        value = _safe_eval(node.value)
        key = _safe_eval(node.slice)
        return value[key]
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in _SAFE_FUNCS:
                fn = _SAFE_FUNCS[func_name]
                args = [_safe_eval(a) for a in node.args]
                return fn(*args)
            if func_name == "range":
                args = [_safe_eval(a) for a in node.args]
                return list(range(*args))
            raise ValueError(f"Unsupported function: {func_name}")
        raise ValueError(f"Unsupported call target: {ast.dump(node.func)}")
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


@tool(
    name="calculate",
    description="Evaluate a mathematical expression safely. Supports +, -, *, /, **, %, min, max, sum, abs, round, sqrt, floor, ceil, range, list literals, comparisons",
    category="data",
    read_only=True,
    tags=["math", "calculate", "computation", "average", "sum"]
)
def calculate(expression: str) -> dict:
    """Evaluate a math expression safely without exec/eval."""
    try:
        tree = ast.parse(expression.strip(), mode='eval')
        result = _safe_eval(tree)
        return {
            "success": True,
            "expression": expression,
            "result": result,
        }
    except Exception as e:
        return {"success": False, "error": f"Calculation error: {e}"}


@tool(
    name="aggregate_data",
    description="Aggregate data (sum, avg, count, min, max)",
    category="data",
    read_only=True,
    tags=["data", "aggregate", "processing"]
)
def aggregate_data(data, field: str = "", operation: str = "sum") -> dict:
    """Aggregate numeric field. Accepts list of numbers, list of dicts, or JSON string."""
    try:
        if isinstance(data, str):
            data = json.loads(data)

        if not isinstance(data, list) or not data:
            return {"success": False, "error": "Data must be a non-empty list of numbers or dicts"}

        if isinstance(data[0], (int, float)):
            values = [x for x in data if isinstance(x, (int, float))]
        elif isinstance(data[0], dict):
            if not field:
                values = []
                for d in data:
                    for v in d.values():
                        if isinstance(v, (int, float)):
                            values.append(v)
            else:
                values = [d.get(field) for d in data if d.get(field) is not None]
        else:
            return {"success": False, "error": "Data must be a list of numbers or dicts"}

        if not values:
            return {"success": False, "error": "No numeric values found"}

        if operation == 'sum':
            result = sum(values)
        elif operation == 'avg':
            result = sum(values) / len(values)
        elif operation == 'count':
            result = len(values)
        elif operation == 'min':
            result = min(values)
        elif operation == 'max':
            result = max(values)
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

        return {
            "success": True,
            "field": field or "values",
            "operation": operation,
            "result": result,
            "count": len(values)
        }
    except json.JSONDecodeError:
        return {"success": False, "error": "Data is not valid JSON"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== System Tools ====================

@tool(
    name="execute_command",
    description="Execute a shell command",
    category="system",
    tags=["system", "command", "shell"]
)
def execute_command(command: str, cwd: Optional[str] = None) -> dict:
    """Execute a shell command."""
    import subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}
