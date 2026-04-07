from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.flight_query_engine.exceptions import DuffelServiceError, OpenAIServiceError
from src.flight_query_engine.schemas.flight_search import (
    FlightResult,
    FlightSegment,
    Price,
)


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
        ):
            resp = await test_client.post("/search", json={"query": "NYC to London"})

        assert resp.status_code == 200
        body = resp.json()
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
        ):
            resp = await test_client.post("/search", json={"query": "NYC to London"})

        assert resp.status_code == 200
        assert resp.json()["results"] == []
        assert resp.json()["metadata"]["results_count"] == 0


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
