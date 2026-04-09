from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.flight_query_engine.exceptions import DuffelServiceError, OfferNotFoundError, OpenAIServiceError
from src.flight_query_engine.schemas.flight_search import (
    FlightResult,
    FlightSegment,
    OfferCondition,
    OfferConditions,
    OfferDetailsResponse,
    OfferPassenger,
    OfferSlice,
    OfferSliceSegment,
    Price,
    PriceBreakdown,
)
from src.flight_query_engine.services.session_store import ConversationTurn, SessionData


@pytest.fixture()
def test_client():
    """Create an async test client that skips lifespan (API key validation)."""
    from src.flight_query_engine.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


class TestSearchEndpoint:
    async def test_successful_search(self, test_client, simple_query):
        mock_result = FlightResult(
            id="off_123",
            price=Price(amount=450.0, currency="GBP"),
            segments=[
                FlightSegment(
                    origin="JFK",
                    destination="LHR",
                    departing_at="2026-06-15T10:00:00",
                    arriving_at="2026-06-15T22:00:00",
                    carrier="BA",
                    flight_number="178",
                    duration="PT7H00M",
                ),
            ],
            total_duration=420,
            stops=0,
        )
        with (
            patch(
                "src.flight_query_engine.api.routes.flight_search.parse_flight_query",
                new_callable=AsyncMock,
                return_value=simple_query,
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.search_flights",
                new_callable=AsyncMock,
                return_value=[mock_result],
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.create_session",
                new_callable=AsyncMock,
                return_value="test-session-id",
            ),
        ):
            resp = await test_client.post("/search", json={"query": "NYC to London"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "test-session-id"
        assert body["parsed_query"]["origin"] == "JFK"
        assert len(body["results"]) == 1
        assert body["results"][0]["price"]["amount"] == 450.0
        assert body["metadata"]["results_count"] == 1

    async def test_empty_results(self, test_client, simple_query):
        with (
            patch(
                "src.flight_query_engine.api.routes.flight_search.parse_flight_query",
                new_callable=AsyncMock,
                return_value=simple_query,
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.search_flights",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.create_session",
                new_callable=AsyncMock,
                return_value="test-session-id",
            ),
        ):
            resp = await test_client.post("/search", json={"query": "NYC to London"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "test-session-id"
        assert body["results"] == []
        assert body["metadata"]["results_count"] == 0


class TestErrorResponses:
    async def test_validation_error_empty_query(self, test_client):
        resp = await test_client.post("/search", json={"query": ""})
        assert resp.status_code == 422
        body = resp.json()
        assert body["type"] == "validation_error"
        assert "message" in body

    async def test_validation_error_missing_query(self, test_client):
        resp = await test_client.post("/search", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["type"] == "validation_error"

    async def test_validation_error_no_body(self, test_client):
        resp = await test_client.post(
            "/search", content="not json", headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["type"] == "validation_error"

    async def test_parse_error(self, test_client):
        with patch(
            "src.flight_query_engine.api.routes.flight_search.parse_flight_query",
            new_callable=AsyncMock,
            side_effect=OpenAIServiceError("Could not understand your query, try rephrasing"),
        ):
            resp = await test_client.post("/search", json={"query": "asdfghjkl"})

        assert resp.status_code == 502
        body = resp.json()
        assert body["type"] == "parse_error"
        assert "rephrasing" in body["message"]

    async def test_search_error(self, test_client, simple_query):
        with (
            patch(
                "src.flight_query_engine.api.routes.flight_search.parse_flight_query",
                new_callable=AsyncMock,
                return_value=simple_query,
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.search_flights",
                new_callable=AsyncMock,
                side_effect=DuffelServiceError("Flight search timed out, please try again"),
            ),
        ):
            resp = await test_client.post("/search", json={"query": "NYC to London"})

        assert resp.status_code == 502
        body = resp.json()
        assert body["type"] == "search_error"
        assert "timed out" in body["message"]

    async def test_unexpected_error(self, test_client):
        with patch(
            "src.flight_query_engine.api.routes.flight_search.parse_flight_query",
            new_callable=AsyncMock,
            side_effect=RuntimeError("something unexpected"),
        ):
            resp = await test_client.post("/search", json={"query": "NYC to London"})

        assert resp.status_code == 500
        body = resp.json()
        assert body["type"] == "server_error"

    async def test_error_response_shape_consistent(self, test_client):
        """All errors must have exactly {type, message} keys."""
        # Validation error
        resp = await test_client.post("/search", json={"query": ""})
        assert set(resp.json().keys()) == {"type", "message"}

        # Service error
        with patch(
            "src.flight_query_engine.api.routes.flight_search.parse_flight_query",
            new_callable=AsyncMock,
            side_effect=OpenAIServiceError(),
        ):
            resp = await test_client.post("/search", json={"query": "test"})
        assert set(resp.json().keys()) == {"type", "message"}


class TestHealthEndpoint:
    async def test_health(self, test_client):
        resp = await test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestFollowUpEndpoint:
    async def test_follow_up_success(self, test_client, simple_query, follow_up_query):
        session = SessionData(
            session_id="sess-123",
            turns=[ConversationTurn(user_query="NYC to London", parsed_query=simple_query)],
        )
        with (
            patch(
                "src.flight_query_engine.api.routes.flight_search.get_session",
                new_callable=AsyncMock,
                return_value=session,
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.parse_follow_up_query",
                new_callable=AsyncMock,
                return_value=follow_up_query,
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.search_flights",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.add_turn",
                new_callable=AsyncMock,
            ),
        ):
            resp = await test_client.post(
                "/search/follow-up/sess-123", json={"query": "make it cheaper"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "sess-123"
        assert body["parsed_query"]["sort_by"] == "price"
        assert body["parsed_query"]["origin"] == "JFK"

    async def test_follow_up_session_not_found(self, test_client):
        with patch(
            "src.flight_query_engine.api.routes.flight_search.get_session",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await test_client.post(
                "/search/follow-up/nonexistent", json={"query": "make it cheaper"},
            )

        assert resp.status_code == 404
        body = resp.json()
        assert body["type"] == "session_error"
        assert "not found" in body["message"].lower()

    async def test_follow_up_empty_query(self, test_client):
        resp = await test_client.post(
            "/search/follow-up/sess-123", json={"query": ""},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["type"] == "validation_error"

    async def test_follow_up_chain(self, test_client, simple_query, follow_up_query):
        """Two follow-ups in sequence on the same session."""
        session_turn1 = SessionData(
            session_id="sess-123",
            turns=[ConversationTurn(user_query="NYC to London", parsed_query=simple_query)],
        )
        session_turn2 = SessionData(
            session_id="sess-123",
            turns=[
                ConversationTurn(user_query="NYC to London", parsed_query=simple_query),
                ConversationTurn(user_query="make it cheaper", parsed_query=follow_up_query),
            ],
        )

        mock_get_session = AsyncMock(side_effect=[session_turn1, session_turn2])

        with (
            patch(
                "src.flight_query_engine.api.routes.flight_search.get_session",
                mock_get_session,
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.parse_follow_up_query",
                new_callable=AsyncMock,
                return_value=follow_up_query,
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.search_flights",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.flight_query_engine.api.routes.flight_search.add_turn",
                new_callable=AsyncMock,
            ),
        ):
            resp1 = await test_client.post(
                "/search/follow-up/sess-123", json={"query": "make it cheaper"},
            )
            resp2 = await test_client.post(
                "/search/follow-up/sess-123", json={"query": "only direct flights"},
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["session_id"] == "sess-123"
        assert resp2.json()["session_id"] == "sess-123"


class TestFlightDetailsEndpoint:
    @pytest.fixture()
    def mock_offer_response(self):
        return OfferDetailsResponse(
            id="off_123",
            price=PriceBreakdown(total=450.0, base=409.20, tax=40.80, currency="GBP"),
            conditions=OfferConditions(
                change_before_departure=OfferCondition(
                    allowed=True, penalty_amount="50.00", penalty_currency="GBP",
                ),
                refund_before_departure=OfferCondition(allowed=False),
            ),
            slices=[
                OfferSlice(
                    origin="JFK",
                    destination="LHR",
                    duration="PT7H00M",
                    segments=[
                        OfferSliceSegment(
                            origin="JFK",
                            destination="LHR",
                            departing_at="2026-06-15T10:00:00",
                            arriving_at="2026-06-15T22:00:00",
                            carrier="BA",
                            carrier_name="British Airways",
                            flight_number="178",
                            duration="PT7H00M",
                            aircraft="Boeing 777-200",
                        ),
                    ],
                ),
            ],
            passengers=[
                OfferPassenger(id="pas_001", type="adult", baggages=[]),
            ],
            expires_at="2026-07-01T12:00:00Z",
            total_emissions_kg="460",
            owner_name="British Airways",
        )

    async def test_successful_details(self, test_client, mock_offer_response):
        with patch(
            "src.flight_query_engine.api.routes.flight_search.get_offer",
            new_callable=AsyncMock,
            return_value=mock_offer_response,
        ):
            resp = await test_client.get("/flights/off_123")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "off_123"
        assert body["price"]["total"] == 450.0
        assert body["price"]["base"] == 409.20
        assert body["price"]["tax"] == 40.80
        assert body["conditions"]["change_before_departure"]["allowed"] is True
        assert body["conditions"]["refund_before_departure"]["allowed"] is False
        assert len(body["slices"]) == 1
        assert body["slices"][0]["segments"][0]["carrier"] == "BA"
        assert body["slices"][0]["segments"][0]["aircraft"] == "Boeing 777-200"
        assert body["passengers"][0]["type"] == "adult"
        assert body["total_emissions_kg"] == "460"
        assert body["owner_name"] == "British Airways"

    async def test_offer_not_found(self, test_client):
        with patch(
            "src.flight_query_engine.api.routes.flight_search.get_offer",
            new_callable=AsyncMock,
            side_effect=OfferNotFoundError(),
        ):
            resp = await test_client.get("/flights/off_nonexistent")

        assert resp.status_code == 404
        body = resp.json()
        assert body["type"] == "offer_error"
        assert "not found" in body["message"].lower()

    async def test_duffel_error(self, test_client):
        with patch(
            "src.flight_query_engine.api.routes.flight_search.get_offer",
            new_callable=AsyncMock,
            side_effect=DuffelServiceError("Flight search temporarily unavailable"),
        ):
            resp = await test_client.get("/flights/off_123")

        assert resp.status_code == 502
        body = resp.json()
        assert body["type"] == "search_error"
