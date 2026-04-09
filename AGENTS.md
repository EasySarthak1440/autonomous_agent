# Autonomous Agent Development Guidelines

## Setup & Execution
- **Docker (Recommended)**: `docker-compose up --build` then `docker-compose logs -f agent`
  - Starts both Ollama (local LLM) and Agent API services
  - Groq service also available via API key in environment as fallback
  - Agent connects to Groq via HTTPS API
- **Manual**: Install deps with `pip install -r requirements.txt`, set GROQ_API_KEY in .env, run API with `python api/main.py`
  - Set `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL` in .env
  - For email tools, also set SMTP_* variables in .env
- **Ollama Local Setup**: 
  - Install Ollama separately or use Docker service
  - Pull model: `ollama pull llama3.2`
  - API will use Ollama when GROQ_API_KEY not set
- **API Entry Point**: `api/main.py` (FastAPI app)
- **Port**: API runs on 8000 by default
- **Web Dashboard**: Access at http://localhost:8000/ui when API is running

## Development Commands
- **Tests**: `pytest tests/ -v`
- **Format**: `black autonomous_agent/`
- **Lint**: `flake8 autonomous_agent/`
- **Dev Dependencies**: Install with `pip install -e ".[dev]"` or use pytest/black/flake8 from requirements
- **Important**: Tests may require Ollama running for full functionality (mocks used in unit tests)

## Environment Variables
- `GROQ_API_KEY` - Groq API key (required for cloud LLM)
- `GROQ_MODEL` (default: `meta-llama/llama-4-scout-17b-16e-instruct`)
- `GROQ_BASE_URL` (default: `https://api.groq.com/openai/v1`)
- `LOG_LEVEL` (default: `INFO`)
- `OLLAMA_BASE_URL` (default: `http://localhost:11434`) - for local LLM
- `MODEL_NAME` (default: `llama3.2`) - Ollama model to use
- `SMTP_SERVER` (default: `smtp.gmail.com`) - for email tools
- `SMTP_PORT` (default: `587`) - for email tools
- `SMTP_USERNAME` - for email tools
- `SMTP_PASSWORD` - for email tokens

## AI/ML Specific Guidelines
- **Prompt Engineering**: Use clear, specific goals with structured context; version prompts in `.prompts/` directory
- **Token Management**: Monitor token usage via LLM backend metrics; keep context under 80% of model limits
- **Model Selection**: Prefer Groq for latency-sensitive tasks; Ollama for offline/private processing
- **Hallucination Detection**: Enable safety validator checks; cross-verify critical facts with knowledge base
- **Fallback Strategies**: Implement retry logic with exponential backoff; switch to local LLM on cloud API failures
- **Response Validation**: Validate LLM outputs against expected formats; use schema validation for structured responses

## Security & Safety Enhancements
- **AI-specific Safety**: Enable harmful content filtering; validate outputs for hallucinations and bias
- **Data Privacy**: Never log PII or sensitive data; use data masking in audit logs; anonymize training data
- **API Security**: Store LLM keys in secret managers; rotate credentials quarterly; use shortest-lived tokens possible
- **Agent Boundary Controls**: Define explicit tool allowlists per agent role; implement timeout limits on tool execution
- **Adversarial Testing**: Regularly test with prompt injection attempts; validate safety boundaries
- **Explainability**: Log reasoning traces for complex decisions; maintain audit trail of LLM invocations

## Observability & Monitoring
- **Logging Standards**: Use structured JSON logging; include trace IDs, agent state, tool names, and durations
- **Metrics Collection**: Track latency, success rates, token consumption, error rates, and safety interventions
- **Tracing**: Enable distributed tracing for multi-step agent workflows; correlate logs with trace IDs
- **Alerting**: Set thresholds for error rates (>5%), latency spikes (2x baseline), and safety interventions
- **Health Checks**: Monitor LLM API availability, tool connectivity, and resource utilization (CPU, memory)
- **Performance Baselines**: Establish baseline metrics for common task types; detect regressions automatically

## DevOps & Deployment
- **Model Versioning**: Tag LLM configurations; maintain rollback capability for model changes
- **Canary Deployments**: Route 5% of traffic to new agent versions; monitor for anomalies before full rollout
- **A/B Testing**: Test different prompt variations or model configurations with controlled user groups
- **Rollback Procedures**: Automatically revert on health check failures; maintain last-known-good configurations
- **Configuration Management**: Store agent configurations in version control; use environment-specific overrides
- **Resource Scaling**: Scale agent instances based on queue depth; implement autoscaling for peak loads

## Testing & Validation
- **AI-specific Testing**: Use golden datasets for common tasks; validate outputs against expected patterns
- **Edge Case Testing**: Test with ambiguous inputs, contradictory instructions, and boundary values
- **Regression Testing**: Compare agent behavior against baseline versions; detect performance degradations
- **Adversarial Testing**: Regularly test with known attack vectors (prompt injection, jailbreaking attempts)
- **Human-in-the-loop**: Require approval for high-risk operations (data deletion, external communications)
- **Test Data Management**: Use synthetic data for testing; anonymize or mask any production data in tests

## Documentation & Knowledge Sharing
- **Runbooks**: Create procedures for common incidents (LLM downtime, tool failures, performance issues)
- **Knowledge Base**: Document agent learnings in `.knowledge/` directory; tag by topic and success rate
- **Performance Benchmarks**: Track completion rates, average latency, and token efficiency per task type
- **Capacity Planning**: Monitor resource utilization trends; plan scaling based on growth projections
- **Knowledge Transfer**: Maintain decision logs for complex tasks; share successful patterns across agents
- **Change Log**: Document all agent configuration changes with rationale and impact assessment

## Notes
- Requires either Groq API key for cloud LLM or Ollama running for local LLM
- Tool system is modular - see core modules for implementation patterns
- Safety features include pre-execution validation and audit logging
- Agent executes tasks via POST to `/execute` endpoint with goal, description, context, and priority
- Monitor audit logs regularly for safety violations and anomalous behavior
- Keep dependencies updated; monthly security scans recommended for production deployments