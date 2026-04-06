# Autonomous Agent Development Guidelines

## Setup & Execution
- **Docker (Recommended)**: `docker-compose up --build` then `docker-compose logs -f agent`
  - Ollama service available at http://localhost:11434
  - Agent connects to Ollama via internal Docker network
- **Manual**: Install deps with `pip install -r requirements.txt`, start Ollama (`ollama serve`), pull model (`ollama pull llama3.2`), run API with `python api/main.py`
  - Set `OLLAMA_BASE_URL=http://localhost:11434` if not using defaults
- **API Entry Point**: `api/main.py` (FastAPI app)
- **Port**: API runs on 8000 by default

## Development Commands
- **Tests**: `pytest tests/ -v`
- **Format**: `black autonomous_agent/`
- **Lint**: `flake8 autonomous_agent/`
- **Dev Dependencies**: Install with `pip install -e ".[dev]"` or use pytest/black/flake8 from requirements
- **Important**: Tests may require Ollama running for full functionality (mocks used in unit tests)

## Environment Variables
- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `MODEL_NAME` (default: `llama3.2`)
- `LOG_LEVEL` (default: `INFO`)

## Project Structure
- **Core Logic**: `core/` directory (LLM, memory, safety, planning, tool registry)
- **API Layer**: `api/` directory (FastAPI endpoints)
- **Frontend**: `frontend/` directory (HTML/CSS/JS UI served at `/ui`)
- **Tools**: Built-in tools in core modules, custom plugins extensible
- **Tests**: `tests/` directory

## Frontend
- **Access**: `http://localhost:8000/ui` when API is running
- **Features**: Task execution, health dashboard, tools browser, memory viewer, audit log
- **Auto-refresh**: Health status polls every 10 seconds
- **Static files**: Served via FastAPI's `StaticFiles` middleware

## Notes
- Requires Ollama running locally for LLM functionality (unless using external endpoint)
- Tool system is modular - see core modules for implementation patterns
- Safety features include pre-execution validation and audit logging