# Flight Query Engine

AI-powered flight search engine that turns natural language queries into structured flight results. Supports conversational follow-ups — refine your search by saying "make it cheaper" or "try next week."

Built with **FastAPI**, **OpenAI structured outputs**, and the **Duffel Flights API**.

## How It Works

```
User: "Belgrade to Dubai, February, 7 days, 2 people, no checked bags, Fly Dubai"
  ↓
OpenAI (gpt-4o-mini) → structured parsing (IATA codes, dates, passengers, filters)
  ↓
Duffel API → flight offers (filtered, sorted, top 20)
  ↓
User: "make it cheaper" / "only direct flights" / "try next week"
  ↓
Session context (Redis) → OpenAI re-parses with full conversation history → updated results
```

## Features

- **Natural language search** — cities, relative dates ("tomorrow", "next week"), cabin class, airlines
- **Conversational follow-ups** — refine results across multiple turns within a session (30 min TTL)
- **Offer details** — full price breakdown, baggage allowances, change/refund conditions, emissions
- **Structured error responses** — typed errors (`parse_error`, `search_error`, `session_error`, etc.)
- **Filtering & sorting** — by airline, stops, baggage-only, price or duration

## Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI (async) |
| NLP parsing | OpenAI `gpt-4o-mini` with Pydantic structured outputs |
| Flight data | Duffel API (via `httpx`, no SDK) |
| Session storage | Redis (conversation history, 30 min TTL) |
| Validation | Pydantic v2 |
| Logging | structlog |

## Quick Start

```bash
cp .env.example .env
# Add your OPENAI_API_KEY and DUFFEL_API_KEY

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

make dev
```

Or with Docker:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. Interactive docs at [`/docs`](http://localhost:8000/docs).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key |
| `DUFFEL_API_KEY` | — | **Required.** Duffel API key |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `SESSION_TTL_SECONDS` | `1800` | Session expiry (seconds) |
| `APP_ENV` | `development` | `development` exposes full error messages |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `info` | Logging level |

## API Endpoints

### `POST /search`

Initial natural language flight search. Creates a session for follow-ups.

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "London to New York, next Friday, 2 adults, business class"}'
```

**Response** includes `session_id`, `parsed_query`, `results[]`, and `metadata`.

### `POST /search/follow-up/{session_id}`

Refine a previous search using conversation context.

```bash
curl -X POST http://localhost:8000/search/follow-up/{session_id} \
  -H "Content-Type: application/json" \
  -d '{"query": "make it cheaper, only direct flights"}'
```

### `GET /flights/{offer_id}`

Full offer details — price breakdown (base/tax/total), baggage allowances, change/refund conditions, segments with aircraft info, and carbon emissions.

### `GET /health`

Returns `{"status": "ok", "service": "flight-query-engine"}`.

## Development

```bash
make dev        # Run dev server with hot reload
make test       # Run tests
make test-cov   # Run tests with coverage report
make lint       # Lint with ruff
make format     # Auto-format with ruff
make check      # Lint + test
```

## Project Structure

```
src/flight_query_engine/
├── main.py                 # App setup, lifespan, CORS
├── config.py               # Settings from environment
├── exceptions.py           # Custom exceptions + global handlers
├── api/routes/
│   └── flight_search.py    # All endpoints
├── schemas/
│   └── flight_search.py    # Request/response models
└── services/
    ├── openai_service.py   # NLP parsing (structured outputs)
    ├── duffel_service.py   # Flight search + offer details
    └── session_store.py    # Redis session management
```
