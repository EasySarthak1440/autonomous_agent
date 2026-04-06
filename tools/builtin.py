"""
Built-in Tools for the Autonomous Agent
"""

import json
import logging
import os
import re
import smtplib
import sqlite3
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Optional

from . import tool

logger = logging.getLogger(__name__)


# ==================== Data Processing Tools ====================

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


@tool(
    name="write_file",
    description="Write contents to a file on the filesystem",
    category="filesystem",
    tags=["file", "write", "io"]
)
def write_file(path: str, content: str, encoding: str = "utf-8", append: bool = False) -> dict:
    """Write content to a file."""
    try:
        mode = 'a' if append else 'w'
        with open(path, mode, encoding=encoding) as f:
            f.write(content)
        return {
            "success": True,
            "path": path,
            "bytes_written": len(content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="list_directory",
    description="List files and directories in a given path",
    category="filesystem",
    read_only=True,
    tags=["file", "directory", "io"]
)
def list_directory(path: str = ".", pattern: Optional[str] = None) -> dict:
    """List directory contents."""
    try:
        items = os.listdir(path)
        if pattern:
            items = [i for i in items if re.match(pattern, i)]
        return {
            "success": True,
            "path": path,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="file_exists",
    description="Check if a file or directory exists",
    category="filesystem",
    read_only=True,
    tags=["file", "check"]
)
def file_exists(path: str) -> dict:
    """Check if path exists."""
    return {
        "success": True,
        "path": path,
        "exists": os.path.exists(path),
        "is_file": os.path.isfile(path) if os.path.exists(path) else None,
        "is_dir": os.path.isdir(path) if os.path.exists(path) else None
    }


# ==================== Database Tools ====================

@tool(
    name="execute_sqlite",
    description="Execute a SQLite query and return results",
    category="database",
    tags=["database", "sql", "sqlite"]
)
def execute_sqlite(db_path: str, query: str, params: Optional[tuple] = None) -> dict:
    """Execute a SQLite query."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Fetch results
        if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
            results = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in results]
        else:
            conn.commit()
            data = {"rows_affected": cursor.rowcount}
        
        conn.close()
        
        return {
            "success": True,
            "columns": columns,
            "data": data,
            "row_count": len(data) if isinstance(data, list) else 1
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="create_sqlite_table",
    description="Create a table in SQLite database",
    category="database",
    tags=["database", "sql", "sqlite", "create"]
)
def create_sqlite_table(db_path: str, table_name: str, schema: dict) -> dict:
    """Create a table with given schema."""
    try:
        columns = ", ".join([f"{name} {dtype}" for name, dtype in schema.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "table": table_name,
            "schema": schema
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Data Processing Tools ====================

@tool(
    name="parse_json",
    description="Parse JSON string into Python object",
    category="data",
    read_only=True,
    tags=["json", "parse"]
)
def parse_json(json_string: str) -> dict:
    """Parse JSON string."""
    try:
        data = json.loads(json_string)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        return {"success": False, "error": str(e)}


@tool(
    name="to_json",
    description="Convert Python object to JSON string",
    category="data",
    read_only=True,
    tags=["json", "serialize"]
)
def to_json(data: Any, indent: int = 2) -> dict:
    """Convert to JSON."""
    try:
        return {
            "success": True,
            "json": json.dumps(data, indent=indent, default=str)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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
        # Simple condition parsing (field==value, field>value, etc.)
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


@tool(
    name="aggregate_data",
    description="Aggregate data (sum, avg, count, min, max)",
    category="data",
    read_only=True,
    tags=["data", "aggregate", "processing"]
)
def aggregate_data(data: list, field: str = "", operation: str = "sum") -> dict:
    """Aggregate numeric field. Accepts list of numbers or list of dicts."""
    try:
        # Handle plain list of numbers: [1, 2, 3]
        if data and isinstance(data[0], (int, float)):
            values = [x for x in data if isinstance(x, (int, float))]
        # Handle list of dicts: [{"value": 1}, {"value": 2}]
        elif data and isinstance(data[0], dict):
            if not field:
                # If no field given, try to find numeric values
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
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Text Processing Tools ====================

@tool(
    name="extract_emails",
    description="Extract email addresses from text",
    category="text",
    read_only=True,
    tags=["text", "regex", "email"]
)
def extract_emails(text: str) -> dict:
    """Extract email addresses from text."""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, text)
    return {
        "success": True,
        "emails": emails,
        "count": len(emails)
    }


@tool(
    name="extract_urls",
    description="Extract URLs from text",
    category="text",
    read_only=True,
    tags=["text", "regex", "url"]
)
def extract_urls(text: str) -> dict:
    """Extract URLs from text."""
    pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    urls = re.findall(pattern, text)
    return {
        "success": True,
        "urls": urls,
        "count": len(urls)
    }


@tool(
    name="text_summary",
    description="Generate a summary of text",
    category="text",
    read_only=True,
    tags=["text", "summary"]
)
def text_summary(text: str, max_length: int = 200) -> dict:
    """Generate a simple text summary."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= 3:
        summary = text
    else:
        # Take first and last sentences plus middle ones
        summary = sentences[0]
        if len(sentences) > 2:
            summary += " " + " ".join(sentences[1:-1])
        summary += " " + sentences[-1]
    
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    
    return {
        "success": True,
        "original_length": len(text),
        "summary": summary,
        "sentence_count": len(sentences)
    }


# ==================== System Tools ====================

@tool(
    name="get_timestamp",
    description="Get current timestamp",
    category="system",
    read_only=True,
    tags=["system", "time", "timestamp"]
)
def get_timestamp(format: str = "iso") -> dict:
    """Get current timestamp."""
    now = datetime.now()
    
    if format == "iso":
        return {"success": True, "timestamp": now.isoformat()}
    elif format == "unix":
        return {"success": True, "timestamp": int(now.timestamp())}
    elif format == "readable":
        return {"success": True, "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")}
    else:
        return {"success": True, "timestamp": str(now)}


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


@tool(
    name="search_files",
    description="Search for files matching a pattern",
    category="system",
    read_only=True,
    tags=["system", "search", "file"]
)
def search_files(directory: str, pattern: str, recursive: bool = True) -> dict:
    """Search for files matching pattern."""
    import glob
    try:
        if recursive:
            search_pattern = os.path.join(directory, "**", pattern)
            matches = glob.glob(search_pattern, recursive=True)
        else:
            search_pattern = os.path.join(directory, pattern)
            matches = glob.glob(search_pattern)
        
        return {
            "success": True,
            "pattern": pattern,
            "directory": directory,
            "matches": matches,
            "count": len(matches)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Business Process Tools ====================

@tool(
    name="create_reminder",
    description="Create a reminder/task entry",
    category="productivity",
    tags=["task", "reminder", "productivity"]
)
def create_reminder(title: str, description: str = "", due_date: Optional[str] = None, 
                    priority: str = "medium") -> dict:
    """Create a reminder entry."""
    reminder = {
        "id": datetime.now().timestamp(),
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    return {
        "success": True,
        "reminder": reminder
    }


@tool(
    name="send_webhook",
    description="Send data to a webhook URL",
    category="communication",
    tags=["webhook", "http", "api"]
)
def send_webhook(url: str, data: dict, method: str = "POST") -> dict:
    """Send webhook request."""
    import aiohttp
    import asyncio
    
    async def _send():
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data) as response:
                return {
                    "status": response.status,
                    "response": await response.text()
                }
    
    try:
        result = asyncio.run(_send())
        return {
            "success": result["status"] < 400,
            "status": result["status"],
            "response": result["response"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="generate_report",
    description="Generate a formatted report from data",
    category="reporting",
    tags=["report", "generate", "output"]
)
def generate_report(title: str, data: dict, format: str = "text") -> dict:
    """Generate a formatted report."""
    
    if format == "text":
        lines = [
            "=" * 60,
            f"  {title}",
            "=" * 60,
            ""
        ]
        for key, value in data.items():
            lines.append(f"{key}: {value}")
        lines.append("")
        lines.append("=" * 60)
        report = "\n".join(lines)
        
    elif format == "markdown":
        lines = [f"# {title}", ""]
        for key, value in data.items():
            lines.append(f"**{key}**: {value}")
        lines.append("")
        report = "\n".join(lines)
        
    else:
        report = json.dumps({"title": title, **data}, indent=2)
    
    return {
        "success": True,
        "report": report,
        "format": format
    }
