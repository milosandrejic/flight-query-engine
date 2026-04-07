from unittest.mock import AsyncMock, patch

import pytest

from src.flight_query_engine.schemas.flight_search import (
    CabinClass,
    ParsedFlightQuery,
    Passengers,
)


@pytest.fixture()
def simple_query():
    return ParsedFlightQuery(
        origin="JFK",
        destination="LHR",
        departure_date="2026-06-15",
        passengers=Passengers(adults=1),
        cabin_class=CabinClass.ECONOMY,
    )


@pytest.fixture()
def return_query():
    return ParsedFlightQuery(
        origin="JFK",
        destination="LHR",
        departure_date="2026-06-15",
        return_date="2026-06-22",
        passengers=Passengers(adults=2, children=1, infants=1),
        cabin_class=CabinClass.BUSINESS,
    )


@pytest.fixture()
def duration_query():
    return ParsedFlightQuery(
        origin="BEG",
        destination="DXB",
        departure_date="2026-02-01",
        trip_duration_days=7,
        passengers=Passengers(adults=1),
    )


MOCK_DUFFEL_OFFER = {
    "id": "off_123",
    "total_amount": "450.00",
    "total_currency": "GBP",
    "slices": [
        {
            "segments": [
                {
                    "origin": {"iata_code": "JFK"},
                    "destination": {"iata_code": "LHR"},
                    "departing_at": "2026-06-15T10:00:00",
                    "arriving_at": "2026-06-15T22:00:00",
                    "marketing_carrier": {"iata_code": "BA"},
                    "marketing_carrier_flight_number": "178",
                    "duration": "PT7H00M",
                },
            ],
        },
    ],
}


@pytest.fixture()
def mock_duffel_response():
    """Returns a function that creates a mock httpx response pair (offer_request + offers)."""

    def _make(offers=None):
        if offers is None:
            offers = [MOCK_DUFFEL_OFFER]

        offer_request_resp = AsyncMock()
        offer_request_resp.raise_for_status = lambda: None
        offer_request_resp.json.return_value = {"data": {"id": "orq_abc"}}

        offers_resp = AsyncMock()
        offers_resp.raise_for_status = lambda: None
        offers_resp.json.return_value = {"data": offers}

        return [offer_request_resp, offers_resp]

    return _make


@pytest.fixture()
def mock_openai_parsed(simple_query):
    """Patches openai parse_flight_query to return a simple_query."""

    def _make(result=None):
        return patch(
            "src.flight_query_engine.api.routes.flight_search.parse_flight_query",
            new_callable=AsyncMock,
            return_value=result or simple_query,
        )

    return _make


@pytest.fixture()
def mock_duffel_search():
    """Patches duffel search_flights to return empty results."""

    def _make(results=None):
        return patch(
            "src.flight_query_engine.api.routes.flight_search.search_flights",
            new_callable=AsyncMock,
            return_value=results or [],
        )

    return _make
