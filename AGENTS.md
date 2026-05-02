# Autonomous Agent Development Guidelines

## Setup & Execution
- **Docker (Recommended)**: `docker-compose up --build` then `docker-compose logs -f agent`
  - Dockerfile uses `python:3.11-slim`, copies all files, and runs `uvicorn api.main:app`
  - `.env` must exist before `docker-compose build` (it gets `COPY . .` into the image)
  - No `env_file` in docker-compose.yml — GROQ_API_KEY must be in the `.env` at build time
- **Manual**:
  - `pip install -e ".[dev]"` (dev includes pytest, pytest-asyncio, black, flake8)
  - `cp .env.example .env` and add `GROQ_API_KEY`
  - Run: `python api/main.py` (uses uvicorn internally)
- **Web Dashboard**: http://localhost:8000/ui (static files from `frontend/`)
- **API Docs**: http://localhost:8000/docs
- **Prometheus Metrics**: http://localhost:8000/metrics

## Development Workflow
- **Tests**: `pytest tests/ -v` (tests use `sys.path.insert` — no src layout)
  - Async tests require `pytest-asyncio` (`@pytest.mark.asyncio`)
- **Format**: `black autonomous_agent/`
- **Lint**: `flake8 autonomous_agent/`

## Key Environment Variables
- `GROQ_API_KEY` — Required for LLM
- `GROQ_MODEL` — Default: `meta-llama/llama-4-scout-17b-16e-instruct`
- `GROQ_BASE_URL` — Default: `https://api.groq.com/openai/v1`
- `SMTP_*` — Email tool configuration (server, port, username, password)

## Architecture
- **Entrypoint**: `api/main.py` — FastAPI app with lifespan initialization
- **Core packages** (defined in `pyproject.toml`): `api`, `core`, `memory`, `safety`, `planning`, `processes`, `tools`, `automation`
- **`core/agent.py`** — `AutonomousAgent` class: LLM → planner → executor → memory loop
- **`core/llm.py`** — `LLMBackend`: OpenAI-compatible Groq client via aiohttp
- **`tools/__init__.py`** — `ToolRegistry`: auto-registers tools from `tools/builtin.py` and `tools/industry.py` via `@tool` decorator
- **`memory/`** — SQLite-backed memory system (semantic, episodic, procedural, knowledge graph); DB file: `memory.db`
- **`safety/`** — `SafetyValidator`: pattern-based dangerous command blocking, circuit breaker, audit log
- **`planning/`** — Planner and execution engine
- **`automation/`** — Workflow executor (`WorkflowExecutor`)
- Memory module uses **lazy imports** to avoid circular dependencies
- Agent uses **sys.path.insert** for module resolution (no src layout)

## Task Execution API
- POST `/execute` with JSON: `{"goal": "...", "description": "...", "context": {}, "priority": 1-10}`
- POST `/tools/{name}/execute` with JSON parameters to run a tool directly
- POST `/workflows/execute` with `{"workflow_id": "...", "context": {}}`
- Monitor audit logs: GET `/audit`

## Important Notes
- Requires Groq API key — agent starts but health returns "degraded" without it
- SQLite DB (`memory.db`) and `.env` are gitignored
- Python >= 3.10 required (pyproject.toml), Docker image uses 3.11
- Tool system is decorator-based: use `@tool(name="...", description="...")` in `tools/builtin.py` or `tools/industry.py`
- High-risk operations (`data_deletion`, `external_communication`, `system_modification`) require human approval by default
