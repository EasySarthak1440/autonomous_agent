# Autonomous AI Agent for Business Process Automation

A self-contained AI system powered by LLMs that can autonomously execute business processes with minimal human intervention.

## Features

- **LLM-Powered Reasoning**: Uses local LLMs (Ollama/vLLM) for intelligent decision-making
- **Modular Tool System**: 19+ built-in tools + custom plugin architecture
- **Hierarchical Memory**: Semantic, episodic, and procedural memory for learning
- **Planning Engine**: LLM-driven task decomposition and execution
- **Safety Governance**: Pre-execution validation, audit logs, circuit breakers
- **REST API**: FastAPI-based endpoints for integration

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services (Ollama + Agent API)
docker-compose up --build

# Run in background
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f agent
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama
ollama serve

# Pull a model (if not already)
ollama pull llama3.2

# Run the API
python api/main.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/execute` | POST | Execute a task |
| `/tools` | GET | List available tools |
| `/tools/{name}` | GET | Get tool details |
| `/tools/{name}/execute` | POST | Execute a tool directly |
| `/memory` | GET | Get memories |
| `/memory` | POST | Store a memory |
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

### List Tools

```bash
curl http://localhost:8000/tools
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | LLM server URL |
| `MODEL_NAME` | `llama3.2` | Model to use |
| `LOG_LEVEL` | `INFO` | Logging level |

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
```

## Available Tools

- **File Operations**: read_file, write_file, list_directory, file_exists
- **Database**: execute_sqlite, create_sqlite_table
- **Data Processing**: parse_json, to_json, filter_data, aggregate_data
- **Text Processing**: extract_emails, extract_urls, text_summary
- **System**: get_timestamp, execute_command, search_files
- **Business**: create_reminder, send_webhook, generate_report

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

## License

MIT
