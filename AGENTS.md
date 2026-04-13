# Autonomous Agent Development Guidelines

## Setup & Execution
- **Docker (Recommended)**: `docker-compose up --build` then `docker-compose logs -f agent`
- **Manual**: 
  - `pip install -r requirements.txt`
  - Create .env with `GROQ_API_KEY`
  - For email tools: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
  - Run: `python api/main.py`
- **Web Dashboard**: http://localhost:8000/ui
- **API Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

## Development Workflow
- **Tests**: `pytest tests/ -v`
- **Format**: `black autonomous_agent/`
- **Lint**: `flake8 autonomous_agent/`
- **Dev Deps**: `pip install -e ".[dev]"` (includes pytest, black, flake8)

## Key Environment Variables
- `GROQ_API_KEY` - Required for LLM (Groq)
- `GROQ_MODEL` - Default: `meta-llama/llama-4-scout-17b-16e-instruct`
- `SMTP_*` - Email tool configuration (server, port, username, password)

## Task Execution
- **Execute Task**: POST to `/execute` with JSON:
  ```json
  {
    "goal": "Task description",
    "description": "Detailed context",
    "context": {"key": "value"},
    "priority": 5
  }
  ```
- **Examples**: See README.md for curl examples (email, health check, etc.)

## Important Notes
- Requires Groq API key for LLM
- Monitor audit logs: http://localhost:8000/audit
- Tool system is modular - implementations in `core/`, `tools/`, `automation/`
