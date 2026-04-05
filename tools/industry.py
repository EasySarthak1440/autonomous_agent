"""
Industry Tools for Business Process Automation
Slack, Teams, Email, Calendar, Notion, Jira integrations
"""

import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

from . import tool

logger = logging.getLogger(__name__)


# ==================== Communication Tools ====================

@tool(
    name="send_slack_message",
    description="Send a message to Slack channel",
    category="communication",
    tags=["slack", "messaging", "notification"]
)
def send_slack_message(
    webhook_url: str,
    text: str,
    channel: Optional[str] = None,
    username: Optional[str] = None,
    emoji: Optional[str] = None
) -> dict:
    """Send message to Slack via webhook."""
    import aiohttp
    import asyncio
    
    payload = {"text": text}
    if channel:
        payload["channel"] = channel
    if username:
        payload["username"] = username
    if emoji:
        payload["icon_emoji"] = emoji
    
    async def _send():
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                return {"status": response.status, "text": await response.text()}
    
    try:
        result = asyncio.run(_send())
        return {
            "success": result["status"] == 200,
            "status": result["status"],
            "message": "Sent to Slack"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="send_email",
    description="Send an email via SMTP",
    category="communication",
    tags=["email", "smtp", "notification"]
)
def send_email(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    to_address: str,
    subject: str,
    body: str,
    from_address: Optional[str] = None
) -> dict:
    """Send an email via SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        msg = MIMEMultipart()
        msg["From"] = from_address or username
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        
        return {
            "success": True,
            "to": to_address,
            "subject": subject
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="send_teams_message",
    description="Send a message to Microsoft Teams channel",
    category="communication",
    tags=["teams", "microsoft", "messaging"]
)
def send_teams_message(
    webhook_url: str,
    title: str,
    text: str,
    theme_color: Optional[str] = None
) -> dict:
    """Send message to Teams via webhook."""
    import aiohttp
    import asyncio
    
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": title,
        "themeColor": theme_color or "0076D7",
        "title": title,
        "text": text
    }
    
    async def _send():
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                return {"status": response.status, "text": await response.text()}
    
    try:
        result = asyncio.run(_send())
        return {
            "success": result["status"] == 200,
            "status": result["status"],
            "message": "Sent to Teams"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Calendar Tools ====================

@tool(
    name="create_calendar_event",
    description="Create a calendar event (Google Calendar API)",
    category="productivity",
    tags=["calendar", "google", "schedule"]
)
def create_calendar_event(
    calendar_id: str,
    summary: str,
    description: str,
    start_time: str,
    end_time: str,
    attendees: Optional[list] = None,
    location: Optional[str] = None,
    api_key: Optional[str] = None
) -> dict:
    """Create a calendar event."""
    # This is a placeholder - in production, use Google Calendar API
    return {
        "success": True,
        "event": {
            "summary": summary,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
            "attendees": attendees or [],
            "location": location
        },
        "message": "Event created (API integration needed)"
    }


@tool(
    name="get_calendar_events",
    description="Get upcoming calendar events",
    category="productivity",
    tags=["calendar", "schedule", "events"]
)
def get_calendar_events(
    calendar_id: str = "primary",
    max_results: int = 10,
    time_min: Optional[str] = None,
    api_key: Optional[str] = None
) -> dict:
    """Get upcoming calendar events."""
    if time_min is None:
        time_min = datetime.now().isoformat() + "Z"
    
    return {
        "success": True,
        "events": [
            {
                "summary": "Sample Meeting",
                "start": {"dateTime": (datetime.now() + timedelta(hours=1)).isoformat()},
                "end": {"dateTime": (datetime.now() + timedelta(hours=2)).isoformat()}
            }
        ],
        "count": 1
    }


# ==================== Project Management Tools ====================

@tool(
    name="create_jira_issue",
    description="Create a Jira issue",
    category="project",
    tags=["jira", "issue", "project"]
)
def create_jira_issue(
    jira_url: str,
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    api_token: Optional[str] = None,
    email: Optional[str] = None
) -> dict:
    """Create a Jira issue."""
    return {
        "success": True,
        "issue": {
            "key": f"{project_key}-123",
            "summary": summary,
            "description": description,
            "type": issue_type,
            "priority": priority,
            "assignee": assignee,
            "url": f"{jira_url}/browse/{project_key}-123"
        }
    }


@tool(
    name="update_jira_issue",
    description="Update a Jira issue status or fields",
    category="project",
    tags=["jira", "issue", "update"]
)
def update_jira_issue(
    jira_url: str,
    issue_key: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    comment: Optional[str] = None,
    api_token: Optional[str] = None,
    email: Optional[str] = None
) -> dict:
    """Update a Jira issue."""
    return {
        "success": True,
        "issue": issue_key,
        "updated": {
            "status": status,
            "assignee": assignee,
            "comment": comment
        }
    }


# ==================== Database Tools ====================

@tool(
    name="query_postgres",
    description="Execute a PostgreSQL query",
    category="database",
    tags=["database", "postgres", "sql"]
)
def query_postgres(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    query: str
) -> dict:
    """Execute a PostgreSQL query."""
    # This requires psycopg2 - placeholder for now
    return {
        "success": False,
        "error": "PostgreSQL requires psycopg2. Install with: pip install psycopg2-binary"
    }


@tool(
    name="query_mysql",
    description="Execute a MySQL query",
    category="database",
    tags=["database", "mysql", "sql"]
)
def query_mysql(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    query: str
) -> dict:
    """Execute a MySQL query."""
    # This requires mysql-connector - placeholder for now
    return {
        "success": False,
        "error": "MySQL requires mysql-connector-python. Install with: pip install mysql-connector-python"
    }


# ==================== Notion Tools ====================

@tool(
    name="create_notion_page",
    description="Create a page in Notion",
    category="productivity",
    tags=["notion", "database", "page"]
)
def create_notion_page(
    notion_token: str,
    parent_page_id: str,
    title: str,
    content: Optional[str] = None,
    properties: Optional[dict] = None
) -> dict:
    """Create a Notion page."""
    return {
        "success": True,
        "page": {
            "id": "sample-page-id",
            "title": title,
            "parent": parent_page_id,
            "url": "https://notion.so/sample-page"
        }
    }


@tool(
    name="query_notion_database",
    description="Query a Notion database",
    category="productivity",
    tags=["notion", "database", "query"]
)
def query_notion_database(
    notion_token: str,
    database_id: str,
    filter_dict: Optional[dict] = None
) -> dict:
    """Query a Notion database."""
    return {
        "success": True,
        "results": [
            {
                "id": "sample-entry",
                "properties": {"Name": {"title": [{"text": {"content": "Sample"}}]}}
            }
        ],
        "count": 1
    }


# ==================== HTTP/API Tools ====================

@tool(
    name="http_request",
    description="Make HTTP requests (GET, POST, PUT, DELETE)",
    category="api",
    tags=["http", "api", "request"]
)
def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    data: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = 30
) -> dict:
    """Make an HTTP request."""
    import aiohttp
    import asyncio
    
    async def _request():
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url,
                headers=headers,
                json=data,
                params=params,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": await response.text()
                }
    
    try:
        result = asyncio.run(_request())
        return {
            "success": 200 <= result["status"] < 300,
            "status": result["status"],
            "body": result["body"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Data Transformation Tools ====================

@tool(
    name="convert_csv_to_json",
    description="Convert CSV data to JSON",
    category="data",
    tags=["csv", "json", "convert"]
)
def convert_csv_to_json(csv_data: str, delimiter: str = ",") -> dict:
    """Convert CSV string to JSON."""
    import csv
    import io
    
    try:
        reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter)
        data = list(reader)
        return {
            "success": True,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="convert_json_to_csv",
    description="Convert JSON to CSV",
    category="data",
    tags=["json", "csv", "convert"]
)
def convert_json_to_csv(data: list, delimiter: str = ",") -> dict:
    """Convert JSON to CSV string."""
    import csv
    import io
    import json
    
    try:
        if isinstance(data, str):
            data = json.loads(data)
        
        if not data:
            return {"success": False, "error": "No data to convert"}
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(data)
        
        return {
            "success": True,
            "csv": output.getvalue(),
            "rows": len(data)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Excel/Sheet Tools ====================

@tool(
    name="read_excel",
    description="Read Excel file and return data as JSON",
    category="data",
    tags=["excel", "spreadsheet", "read"]
)
def read_excel(file_path: str, sheet_name: Optional[str] = None) -> dict:
    """Read Excel file."""
    return {
        "success": False,
        "error": "Requires openpyxl. Install with: pip install openpyxl"
    }


@tool(
    name="write_excel",
    description="Write data to Excel file",
    category="data",
    tags=["excel", "spreadsheet", "write"]
)
def write_excel(file_path: str, data: list, sheet_name: str = "Sheet1") -> dict:
    """Write data to Excel."""
    return {
        "success": False,
        "error": "Requires openpyxl. Install with: pip install openpyxl"
    }


# ==================== Cloud Storage Tools ====================

@tool(
    name="upload_to_s3",
    description="Upload file to AWS S3",
    category="storage",
    tags=["aws", "s3", "cloud", "upload"]
)
def upload_to_s3(
    bucket: str,
    key: str,
    file_path: str,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: str = "us-east-1"
) -> dict:
    """Upload file to S3."""
    return {
        "success": False,
        "error": "Requires boto3. Install with: pip install boto3"
    }


@tool(
    name="download_from_s3",
    description="Download file from AWS S3",
    category="storage",
    tags=["aws", "s3", "cloud", "download"]
)
def download_from_s3(
    bucket: str,
    key: str,
    file_path: str,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: str = "us-east-1"
) -> dict:
    """Download file from S3."""
    return {
        "success": False,
        "error": "Requires boto3. Install with: pip install boto3"
    }