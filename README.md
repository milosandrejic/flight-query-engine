# Flight Query Engine

AI-powered flight search — send a natural language query, get structured flight results back.

Built with FastAPI, OpenAI structured outputs, and the Duffel flights API.

## Stack

- **FastAPI** — async web framework
- **OpenAI** — natural language parsing (structured outputs with Pydantic)
- **Duffel API** — flight search (via httpx, no SDK)
- **Pydantic** — validation, serialization, OpenAPI docs

## Quick Start

```bash
# Setup
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and DUFFEL_API_KEY

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run
uvicorn src.flight_query_engine.main:app --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/search` | Natural language flight search |

## API Docs

Visit `http://localhost:8000/docs` for interactive Swagger UI.

## Docker

```bash
docker compose up --build
```

## Scripts

```bash
# Development server
uvicorn src.flight_query_engine.main:app --reload

# Lint
ruff check src/ tests/

# Run tests
pytest
```

## References

- [plan.md](plan.md) — Implementation plan and improvements
