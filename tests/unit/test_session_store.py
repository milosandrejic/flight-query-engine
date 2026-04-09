import pytest

import fakeredis.aioredis

from src.flight_query_engine.schemas.flight_search import (
    CabinClass,
    ParsedFlightQuery,
    Passengers,
)
from src.flight_query_engine.services import session_store
from src.flight_query_engine.services.session_store import (
    add_turn,
    create_session,
    get_session,
)


@pytest.fixture(autouse=True)
async def _fake_redis():
    """Replace the session store Redis client with fakeredis for each test."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    session_store._redis = fake
    yield
    await fake.aclose()
    session_store._redis = None


@pytest.fixture()
def sample_query():
    return ParsedFlightQuery(
        origin="JFK",
        destination="LHR",
        departure_date="2026-06-15",
        passengers=Passengers(adults=1),
        cabin_class=CabinClass.ECONOMY,
    )


@pytest.fixture()
def another_query():
    return ParsedFlightQuery(
        origin="JFK",
        destination="LHR",
        departure_date="2026-06-15",
        passengers=Passengers(adults=1),
        cabin_class=CabinClass.ECONOMY,
        sort_by="price",
    )


class TestCreateSession:
    async def test_returns_uuid(self, sample_query):
        import uuid

        session_id = await create_session("NYC to London", sample_query)
        uuid.UUID(session_id)  # raises if not valid UUID

    async def test_session_retrievable_after_create(self, sample_query):
        session_id = await create_session("NYC to London", sample_query)
        session = await get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert len(session.turns) == 1
        assert session.turns[0].user_query == "NYC to London"
        assert session.turns[0].parsed_query.origin == "JFK"


class TestGetSession:
    async def test_returns_none_for_unknown(self):
        session = await get_session("nonexistent-id")
        assert session is None

    async def test_returns_session_data(self, sample_query):
        session_id = await create_session("NYC to London", sample_query)
        session = await get_session(session_id)
        assert session is not None
        assert session.turns[0].parsed_query.destination == "LHR"


class TestAddTurn:
    async def test_appends_turn(self, sample_query, another_query):
        session_id = await create_session("NYC to London", sample_query)
        await add_turn(session_id, "make it cheaper", another_query)

        session = await get_session(session_id)
        assert session is not None
        assert len(session.turns) == 2
        assert session.turns[1].user_query == "make it cheaper"
        assert session.turns[1].parsed_query.sort_by == "price"

    async def test_unknown_session_raises(self, sample_query):
        with pytest.raises(KeyError, match="not found"):
            await add_turn("nonexistent-id", "make it cheaper", sample_query)


class TestSessionTTL:
    async def test_session_has_ttl(self, sample_query):
        session_id = await create_session("NYC to London", sample_query)
        ttl = await session_store._redis.ttl(f"session:{session_id}")
        assert ttl > 0
        assert ttl <= 1800
