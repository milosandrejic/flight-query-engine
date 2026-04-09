from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.flight_query_engine.api.routes.flight_search import router as flight_search_router
from src.flight_query_engine.config import settings
from src.flight_query_engine.exceptions import ConfigError, FlightQueryEngineError
from src.flight_query_engine.services.session_store import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not settings.openai_api_key:
        raise ConfigError("OPENAI_API_KEY is not set")
    if not settings.duffel_api_key:
        raise ConfigError("DUFFEL_API_KEY is not set")
    await init_redis()
    try:
        yield
    finally:
        await close_redis()

app = FastAPI(
    title="Flight Query Engine",
    description="AI-powered flight search with structured parsing",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    first_error = exc.errors()[0]
    return JSONResponse(
        status_code=422,
        content={"type": "validation_error", "message": first_error["msg"]},
    )


@app.exception_handler(FlightQueryEngineError)
async def app_error_handler(request: Request, exc: FlightQueryEngineError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"type": exc.error_type, "message": exc.message},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    message = str(exc) if settings.is_development else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"type": "server_error", "message": message},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flight_search_router)

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "flight-query-engine",
    }
