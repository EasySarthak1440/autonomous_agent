# Autonomous Agent Development Guidelines

## Setup & Execution
- **Docker (Recommended)**: `docker-compose up --build` then `docker-compose logs -f agent`
  - Shows real-time logs; Ollama starts on :11434, Agent API on :8000
- **Manual**: 
  - `pip install -r requirements.txt`
  - Create .env with:
    - `GROQ_API_KEY` (for cloud LLM) OR set up Ollama
    - For Ollama: install Ollama, run `ollama serve`, `ollama pull llama3.2`
    - For email tools: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
  - Run: `python api/main.py`
- **Web Dashboard**: http://localhost:8000/ui
- **API Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

## Development Workflow
- **Tests**: `pytest tests/ -v` (may require Ollama running for full functionality)
- **Format**: `black autonomous_agent/`
- **Lint**: `flake8 autonomous_agent/`
- **Dev Deps**: `pip install -e ".[dev]"` (includes pytest, black, flake8)

## Key Environment Variables
- `GROQ_API_KEY` - Required for cloud LLM (Groq)
- `OLLAMA_BASE_URL` - Default: `http://localhost:11434` (for local LLM)
- `MODEL_NAME` - Default: `llama3.2` (Ollama model)
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
- Requires either Groq API key OR Ollama running locally
- Monitor audit logs: http://localhost:8000/audit
- Tool system is modular - implementations in `core/`, `tools/`, `automation/`