import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter

from src.flight_query_engine.schemas.flight_search import (
    FlightSearchRequest,
    FlightSearchResponse,
    SearchMetadata,
)
from src.flight_query_engine.services.duffel_service import search_flights
from src.flight_query_engine.services.openai_service import parse_flight_query

router = APIRouter(tags=["flight-search"])


@router.post("/search", response_model=FlightSearchResponse)
async def flight_search(body: FlightSearchRequest) -> FlightSearchResponse:
    start = time.monotonic()

    parsed_query = await parse_flight_query(body.query)
    results = await search_flights(parsed_query)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    return FlightSearchResponse(
        parsed_query=parsed_query,
        results=results,
        metadata=SearchMetadata(
            search_id=uuid.uuid4(),
            results_count=len(results),
            search_time_ms=elapsed_ms,
            timestamp=datetime.now(UTC).isoformat(),
        ),
    )
