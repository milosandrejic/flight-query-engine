# Flight Query Engine — Implementation Plan

Python rewrite of [flight-search-ai](https://github.com/milosandrejic/flight-search-ai) (NestJS) with improvements.

## Steps (commit after each)

### Step 1: Config + Structured Logging
- [x] `config.py` — pydantic-settings, loads .env, validates at startup
- [x] `core/logging.py` — structlog setup (replaces Pino)
- [x] Wire into `main.py` with lifespan, CORS, health endpoint
- **Commit:** `feat: config, structured logging, health endpoint`

### Step 2: Database + ORM Model
- [ ] `database/session.py` — async SQLAlchemy engine + session factory
- [ ] `models/search_history.py` — SearchHistory SQLAlchemy model
- [ ] `api/deps.py` — FastAPI dependency for DB session
- **Commit:** `feat: async database setup and search history model`

### Step 3: Pydantic Schemas + Custom Exceptions
- [ ] `schemas/chat.py` — ChatRequest, ChatResponse, ParsedFlightQuery, FlightResult
- [ ] `core/exceptions.py` — custom exceptions (ExternalApiError, AiValidationError, etc.)
- [ ] `core/exception_handlers.py` — global error handler middleware
- **Commit:** `feat: request/response schemas and error handling`

### Step 4: Search History Service + Routes
- [ ] `services/search_history.py` — create, findByUser, getPopularRoutes
- [ ] `api/routes/search.py` — GET /searches/history, GET /searches/popular
- **Commit:** `feat: search history service and routes`

### Step 5: OpenAI Service
- [ ] `services/openai_service.py` — structured output via function calling
- **Improvement:** uses OpenAI structured outputs (Pydantic schema) instead of raw JSON prompting
- **Commit:** `feat: openai structured output service`

### Step 6: Duffel Service
- [ ] `services/duffel_service.py` — async flight search via httpx (no SDK dependency)
- **Improvement:** uses httpx directly instead of @duffel/api SDK — lighter, async-native
- **Commit:** `feat: duffel flight search service`

### Step 7: Chat Route (Full Pipeline)
- [ ] `api/routes/chat.py` — POST /chat (parse → search → save history)
- [ ] `services/flight_query_parser.py` — orchestrates OpenAI parsing + validation
- **Commit:** `feat: chat endpoint with full search pipeline`

### Step 8: Alembic Migrations
- [ ] `alembic.ini` + `alembic/env.py` — async migration setup
- [ ] Initial migration: create search_history table (run after DB is up)
- **Commit:** `feat: alembic migration setup`

### Step 9: Final Wiring + Docker
- [ ] Update Dockerfile + docker-compose for full stack
- [ ] README with setup instructions
- **Commit:** `feat: docker setup and documentation`

## Key Improvements over NestJS Version
1. **Async-native** — asyncpg + httpx, real concurrency
2. **OpenAI structured outputs** — Pydantic schema enforcement, no JSON parsing hacks
3. **Fewer layers** — routes → services → models (no repository pattern)
4. **Pydantic everywhere** — one model for validation + serialization + OpenAPI docs
5. **httpx instead of Duffel SDK** — lighter dependency, full async
6. **Alembic** — safer migrations via model diffing
7. **structlog** — better structured logging than Pino
