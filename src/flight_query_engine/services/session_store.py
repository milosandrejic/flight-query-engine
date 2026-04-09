import json
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis

from src.flight_query_engine.config import settings
from src.flight_query_engine.schemas.flight_search import ParsedFlightQuery

SESSION_PREFIX = "session:"

_redis: Redis | None = None


@dataclass
class ConversationTurn:
    user_query: str
    parsed_query: ParsedFlightQuery


@dataclass
class SessionData:
    session_id: str
    turns: list[ConversationTurn]


def _get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized — call init_redis() first")
    return _redis


async def init_redis(redis_url: str | None = None) -> None:
    """Initialize Redis connection. Called from app lifespan."""
    global _redis  # noqa: PLW0603
    url = redis_url or settings.redis_url
    _redis = Redis.from_url(url, decode_responses=True)


async def close_redis() -> None:
    """Close Redis connection. Called from app lifespan."""
    global _redis  # noqa: PLW0603
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _serialize_turns(turns: list[ConversationTurn]) -> str:
    return json.dumps(
        [
            {"user_query": t.user_query, "parsed_query": t.parsed_query.model_dump()}
            for t in turns
        ],
    )


def _deserialize_turns(raw: str) -> list[ConversationTurn]:
    data = json.loads(raw)
    return [
        ConversationTurn(
            user_query=t["user_query"],
            parsed_query=ParsedFlightQuery.model_validate(t["parsed_query"]),
        )
        for t in data
    ]


async def create_session(user_query: str, parsed_query: ParsedFlightQuery) -> str:
    """Create a new session with the first conversation turn. Returns session_id."""
    redis = _get_redis()
    session_id = str(uuid.uuid4())
    turns = [ConversationTurn(user_query=user_query, parsed_query=parsed_query)]
    await redis.set(
        f"{SESSION_PREFIX}{session_id}",
        _serialize_turns(turns),
        ex=settings.session_ttl_seconds,
    )
    return session_id


async def get_session(session_id: str) -> SessionData | None:
    """Load session from Redis. Returns None if expired or missing."""
    redis = _get_redis()
    raw = await redis.get(f"{SESSION_PREFIX}{session_id}")
    if raw is None:
        return None
    return SessionData(session_id=session_id, turns=_deserialize_turns(raw))


async def add_turn(session_id: str, user_query: str, parsed_query: ParsedFlightQuery) -> None:
    """Append a follow-up turn to an existing session. Resets TTL."""
    redis = _get_redis()
    key = f"{SESSION_PREFIX}{session_id}"
    raw = await redis.get(key)
    if raw is None:
        raise KeyError(f"Session {session_id} not found")
    turns = _deserialize_turns(raw)
    turns.append(ConversationTurn(user_query=user_query, parsed_query=parsed_query))
    await redis.set(key, _serialize_turns(turns), ex=settings.session_ttl_seconds)
