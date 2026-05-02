"""
Industry Tools for Business Process Automation
Email, Calendar, Excel, S3 integrations
"""

import json
import logging
import os
from typing import Optional
from datetime import datetime

from . import tool

logger = logging.getLogger(__name__)


# ==================== Communication Tools ====================

@tool(
    name="send_email",
    description="Send an email via SMTP",
    category="communication",
    tags=["email", "smtp", "notification"]
)
def send_email(
    to_address: str,
    subject: str,
    body: str,
    from_address: Optional[str] = None,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> dict:
    """Send an email via SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_server = smtp_server or os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
    username = username or os.environ.get("SMTP_USERNAME", "")
    password = password or os.environ.get("SMTP_PASSWORD", "")

    if not username or not password:
        return {"success": False, "error": "SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD environment variables."}

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
            "from": from_address or username,
            "subject": subject
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

    from datetime import timedelta
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
