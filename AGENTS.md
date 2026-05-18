# Autonomous Agent Development Guidelines

## Setup & Execution
- **Docker (Recommended)**: `docker-compose up --build` then `docker-compose logs -f agent`
  - Dockerfile installs from `requirements.txt` (NOT `pyproject.toml`)
  - `.env` must exist before `docker-compose build` — `COPY . .` copies it in; no `env_file` in docker-compose.yml
  - `GROQ_API_KEY` must be in `.env` at build time (not injected at runtime)
- **Manual**:
  - `pip install -e ".[dev]"` or `pip install -r requirements.txt`
  - `cp .env.example .env` and add `GROQ_API_KEY` (`.env.example` only has SMTP vars)
  - Run: `python api/main.py` (loads `.env` via `load_dotenv()` in `api/main.py:13`)
- **Web Dashboard**: http://localhost:8000/ui (static files from `frontend/`)
- **API Docs**: http://localhost:8000/docs
- **Prometheus Metrics**: http://localhost:8000/metrics

## Development Workflow
- **Tests**: `pytest tests/ -v` (no conftest.py, no pytest.ini — each test file uses `sys.path.insert` for root)
  - Async tests require `@pytest.mark.asyncio`
  - Tests import top-level packages directly (`from core.agent import ...`)
- **Format**: `black autonomous_agent/`
- **Lint**: `flake8 autonomous_agent/`
- **Order**: format → lint → test

## Key Environment Variables
- `GROQ_API_KEY` — Required for LLM (agent starts without it, health returns "degraded")
- `GROQ_MODEL` — Default: `meta-llama/llama-4-scout-17b-16e-instruct`
- `GROQ_BASE_URL` — Default: `https://api.groq.com/openai/v1`
- `SMTP_*` — Email tool (server, port, username, password)

## Architecture
- **Entrypoint**: `api/main.py` — FastAPI app with lifespan that initializes `AutonomousAgent` and `WorkflowExecutor`
- **Core packages**: `api`, `core`, `memory`, `safety`, `planning`, `processes`, `tools`, `automation`
- **`core/agent.py`** — `AutonomousAgent`: LLM → planner → executor → memory loop
- **`core/llm.py`** — `LLMBackend`: OpenAI-compatible Groq client via aiohttp
- **`tools/__init__.py`** — `ToolRegistry` auto-registers tools from `tools/builtin.py` and `tools/industry.py` on init
  - New tools: use `@tool(name="...", description="...")` decorator or `registry.register()`
- **`memory/`** — SQLite-backed memory (semantic, episodic, procedural, knowledge graph); DB: `memory.db`
  - Uses lazy imports to avoid circular dependencies
- **`safety/`** — `SafetyValidator`: pattern-based command blocking, circuit breaker, audit log
- **`planning/`** — Planner and execution engine
- **`automation/`** — `WorkflowExecutor`
- No src layout — modules resolve via `sys.path.insert` at runtime

## Task Execution API
- POST `/execute` — `{"goal": "...", "description": "...", "context": {}, "priority": 1-10}`
- POST `/tools/{name}/execute` — direct tool execution with JSON params
- POST `/workflows/execute` — `{"workflow_id": "...", "context": {}}`
- GET `/audit` — safety audit log
- GET `/health` — status: "healthy" or "degraded" (depends on LLM availability)

## Important Notes
- SQLite DB (`memory.db`, `*.db`) and `.env` are gitignored
- Python >= 3.10 (pyproject.toml), Docker uses 3.11
- High-risk tools (`data_deletion`, `external_communication`, `system_modification`) require human approval by default
- `requirements.txt` has `prometheus_client`; `pyproject.toml` does not — Docker uses `requirements.txt`
