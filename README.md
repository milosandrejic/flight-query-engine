# Flight Query Engine

AI-powered Flight Query Engine with Structured Parsing and API Orchestration (FastAPI + LLM)

## Stack

- **FastAPI** — async web framework
- **PostgreSQL** — database (SQLAlchemy async + Alembic)
- **OpenAI** — natural language parsing (structured outputs)
- **Duffel API** — flight search (via httpx)
- **structlog** — structured logging
- **Pydantic** — validation, serialization, OpenAPI docs

## Quick Start

```bash
# Start database
docker compose -f docker-compose.dev.yml up -d

# Setup
cp .env.example .env
# Edit .env with your API keys
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Run
uvicorn src.flight_query_engine.main:app --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Natural language flight search |
| GET | `/searches/history?user_id=...` | User search history |
| GET | `/searches/popular` | Popular routes |

## API Docs

Visit `http://localhost:8000/docs` for interactive Swagger UI.

## Scripts

```bash
# Development server
uvicorn src.flight_query_engine.main:app --reload

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## References

- [plan.md](plan.md) — Implementation plan and improvements
