# Autonomous Agent Development Guidelines

## Setup & Execution
- **Docker (Recommended)**: `docker-compose up --build` then `docker-compose logs -f agent`
  - Groq service available via API key in environment
  - Agent connects to Groq via HTTPS API
- **Manual**: Install deps with `pip install -r requirements.txt`, set GROQ_API_KEY in .env, run API with `python api/main.py`
  - Set `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL` in .env
- **API Entry Point**: `api/main.py` (FastAPI app)
- **Port**: API runs on 8000 by default

## Development Commands
- **Tests**: `pytest tests/ -v`
- **Format**: `black autonomous_agent/`
- **Lint**: `flake8 autonomous_agent/`
- **Dev Dependencies**: Install with `pip install -e ".[dev]"` or use pytest/black/flake8 from requirements
- **Important**: Tests may require Ollama running for full functionality (mocks used in unit tests)

## Environment Variables
- `GROQ_API_KEY` - Groq API key (required)
- `GROQ_MODEL` (default: `meta-llama/llama-4-scout-17b-16e-instruct`)
- `GROQ_BASE_URL` (default: `https://api.groq.com/openai/v1`)
- `LOG_LEVEL` (default: `INFO`)

## Notes
- Requires Groq API key for LLM functionality
- Tool system is modular - see core modules for implementation patterns
- Safety features include pre-execution validation and audit logging