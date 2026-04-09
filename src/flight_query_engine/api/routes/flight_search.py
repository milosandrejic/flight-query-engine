import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter

from src.flight_query_engine.exceptions import SessionNotFoundError
from src.flight_query_engine.schemas.flight_search import (
    FlightSearchRequest,
    FlightSearchResponse,
    FollowUpRequest,
    FollowUpResponse,
    OfferDetailsResponse,
    SearchMetadata,
)
from src.flight_query_engine.services.duffel_service import get_offer, search_flights
from src.flight_query_engine.services.openai_service import parse_flight_query, parse_follow_up_query
from src.flight_query_engine.services.session_store import add_turn, create_session, get_session

router = APIRouter(tags=["flight-search"])


@router.post("/search", response_model=FlightSearchResponse)
async def flight_search(body: FlightSearchRequest) -> FlightSearchResponse:
    start = time.monotonic()

    parsed_query = await parse_flight_query(body.query)
    results = await search_flights(parsed_query)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    session_id = await create_session(body.query, parsed_query)

    return FlightSearchResponse(
        session_id=session_id,
        parsed_query=parsed_query,
        results=results,
        metadata=SearchMetadata(
            search_id=uuid.uuid4(),
            results_count=len(results),
            search_time_ms=elapsed_ms,
            timestamp=datetime.now(UTC).isoformat(),
        ),
    )


@router.post("/search/follow-up/{session_id}", response_model=FollowUpResponse)
async def follow_up_search(session_id: str, body: FollowUpRequest) -> FollowUpResponse:
    session = await get_session(session_id)
    if session is None:
        raise SessionNotFoundError()

    start = time.monotonic()

    parsed_query = await parse_follow_up_query(session.turns, body.query)
    results = await search_flights(parsed_query)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    await add_turn(session_id, body.query, parsed_query)

    return FollowUpResponse(
        session_id=session_id,
        parsed_query=parsed_query,
        results=results,
        metadata=SearchMetadata(
            search_id=uuid.uuid4(),
            results_count=len(results),
            search_time_ms=elapsed_ms,
            timestamp=datetime.now(UTC).isoformat(),
        ),
    )


@router.get("/flights/{offer_id}", response_model=OfferDetailsResponse)
async def flight_details(offer_id: str) -> OfferDetailsResponse:
    return await get_offer(offer_id)
