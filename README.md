# Autonomous AI Agent for Business Process Automation

A self-contained AI system powered by LLMs that can autonomously execute business processes with minimal human intervention. Features a modern dark-themed web dashboard for easy interaction.
Open source and community-driven - contributions welcome!

## About

This project is an **autonomous AI agent** designed to automate business processes using Large Language Models. It combines LLM-powered reasoning with a modular tool system to understand goals, create execution plans, and complete tasks autonomously.

**Key Capabilities:**
- Understand natural language goals and break them into executable steps
- Learn from past executions using hierarchical memory (semantic, episodic, procedural)
- Execute tasks using built-in tools (file operations, databases, data processing, email, etc.)
- Validate actions through safety checks and audit logging
- Monitor performance via Prometheus metrics and structured logging

**Built With:**
- **Groq API** - Fast LLM inference for reasoning and planning
- **FastAPI** - REST API for integration and web dashboard
- **SQLite** - Local memory and knowledge storage
- **Prometheus** - Metrics and observability

This is suitable for developers building AI-powered automation, researchers exploring autonomous agents, or businesses looking to streamline workflows with LLMs.

## Features

- **LLM-Powered Reasoning**: Uses Groq API for intelligent decision-making
- **Modern Web Dashboard**: Dark-themed UI for task execution, tool management, and monitoring
- **Modular Tool System**: Built-in tools for files, databases, data processing, email (SMTP), calendar, Excel, and S3 (some require extra packages)
- **Hierarchical Memory**: Semantic, episodic, and procedural memory for learning
- **Planning Engine**: LLM-driven task decomposition and execution with fallback strategies
- **AI/ML Enhancements**: Token management, hallucination detection, prompt engineering best practices
- **Security & Safety**: Enhanced validation, harmful content filtering, data privacy controls, adversarial testing
- **Observability**: Structured logging, metrics collection, distributed tracing, health monitoring
- **DevOps Ready**: Model versioning, canary deployments, A/B testing, rollback procedures
- **Comprehensive Testing**: AI-specific testing, edge case validation, regression testing, human-in-the-loop
- **REST API**: FastAPI-based endpoints for integration

## Quick Start

### Using Docker Compose (Recommended)

```bash
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f agent
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - GROQ_API_KEY (required for LLM)
# - SMTP_* variables for email tools

# Run the API
python api/main.py
```

## Web Dashboard

Access the dashboard at **http://localhost:8000/ui** when the API is running.

Features:
- **System Health** - Real-time agent status, LLM connection, tools count, memory stats
- **Task Execution** - Submit natural language goals for LLM-powered planning
- **Tools Browser** - Browse all available tools with descriptions
- **Memory Viewer** - View and clear stored agent memories
- **Audit Log** - Safety validation event history

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/execute` | POST | Execute a task |
| `/tools` | GET | List available tools |
| `/tools/{name}` | GET | Get tool details |
| `/memory` | GET | Get memories |
| `/memory` | POST | Store a memory |
| `/memory` | DELETE | Clear all memories |
| `/memory/statistics` | GET | Memory statistics |
| `/audit` | GET | Safety audit log |

## Example Usage

### Execute a Task

```bash
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Generate a sales report for Q1 2024",
    "description": "Create a comprehensive sales report",
    "context": {"department": "sales"},
    "priority": 5
  }'
```

### Send an Email

```bash
curl -X POST http://localhost:8000/tools/send_email/execute \
  -H "Content-Type: application/json" \
  -d '{
    "to_address": "recipient@example.com",
    "subject": "Hello",
    "body": "This is a test email.",
    "from_address": "sender@gmail.com",
    "username": "sender@gmail.com",
    "password": "your_app_password"
  }'
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Environment Variables

### LLM Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | - | Groq API key (required) |
| `GROQ_MODEL` | `meta-llama/llama-4-scout-17b-16e-instruct` | LLM model to use |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq API base URL |
| `LOG_LEVEL` | `INFO` | Logging level |

### Email Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_SERVER` | `smtp.gmail.com` | SMTP server for email |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | - | SMTP username (email address) |
| `SMTP_PASSWORD` | - | SMTP password (app password for Gmail) |

### Monitoring & Observability
| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_PROMETHEUS_METRICS` | `true` | Enable Prometheus metrics endpoint at /metrics |
| `METRICS_PORT` | `8000` | Port for metrics server (same as API) |

### Enhanced Features (2026 Standards)
| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_STRUCTURED_LOGGING` | `true` | Enable structured JSON logging with trace IDs |
| `ENABLE_METRICS_COLLECTION` | `true` | Enable metrics collection for monitoring systems |
| `ENABLE_TRACING` | `true` | Enable distributed tracing for workflow monitoring |
| `ENABLE_HALLUCINATION_DETECTION` | `true` | Enable LLM output hallucination detection |
| `ENABLE_FALLBACK_STRATEGIES` | `true` | Enable fallback mechanisms for planning failures |
| `ENABLE_HUMAN_IN_THE_LOOP` | `true` | Require human approval for high-risk operations |
| `CANARY_PERCENTAGE` | `5` | Percentage of traffic for canary deployments |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Autonomous Agent                    │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │    LLM   │  │  Memory  │  │  Safety  │            │
│  │ Backend  │  │  System  │  │ Validator│            │
│  └──────────┘  └──────────┘  └──────────┘            │
│  ┌──────────────────────────────────────────────────┐ │
│  │              Tool Registry                        │ │
│  │  [File] [DB] [Data] [Text] [System] [+Custom]   │ │
│  │  [Email] [Slack] [Teams] [S3] [HTTP] [Excel]    │ │
│  └──────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────┐ │
│  │           Planning & Execution Engine            │ │
│  └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │  FastAPI   │
                   │    REST    │
                   └─────────────┘
                           │
                           ▼
                   ┌─────────────┐
                   │   Web UI   │
                   │  (Dark)    │
                   └─────────────┘
```

## Available Tools

12 tools are currently registered:

- **Filesystem**: `read_file`
- **Database**: `sql_manager` — full SQLite support (SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, JOIN, etc.)
- **Data Processing**: `filter_data`, `aggregate_data` (sum, avg, count, min, max), `calculate` (safe math expression evaluator)
- **System**: `execute_command` (shell commands, 30s timeout)
- **Communication**: `send_email` (SMTP, requires `SMTP_USERNAME`/`SMTP_PASSWORD`)
- **Productivity**: `create_calendar_event`, `get_calendar_events` (stubs — API integration needed)
- **Excel**: `read_excel`, `write_excel` (require `openpyxl` — not installed by default)
- **Cloud Storage**: `download_from_s3` (requires `boto3` — not installed by default)

### Adding New Tools

Place them in `tools/builtin.py` or `tools/industry.py` using the `@tool` decorator:

```python
from . import tool

@tool(name="my_tool", description="Does something", category="my_category")
def my_tool(arg1: str) -> dict:
    return {"result": arg1}
```

The `ToolRegistry` auto-registers tools from these modules on import.

## Safety Features

- Pre-execution action validation
- Pattern-based dangerous command blocking
- Audit logging of all actions
- Circuit breaker for repeated failures
- Configurable human-in-the-loop checkpoints

## Development

```bash
# Run tests
pytest tests/ -v

# Format code
black autonomous_agent/

# Lint
flake8 autonomous_agent/
```

