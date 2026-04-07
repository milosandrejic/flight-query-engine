from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.flight_query_engine.exceptions import DuffelServiceError
from src.flight_query_engine.services.duffel_service import search_flights


class TestSearchFlightsErrors:
    @pytest.fixture(autouse=True)
    def _patch_httpx(self):
        self.mock_client = AsyncMock()
        patcher = patch("src.flight_query_engine.services.duffel_service.httpx.AsyncClient")
        mock_cls = patcher.start()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=self.mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield
        patcher.stop()

    async def test_timeout_raises_search_error(self, simple_query):
        self.mock_client.post.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(DuffelServiceError, match="timed out"):
            await search_flights(simple_query)

    async def test_401_raises_misconfigured(self, simple_query):
        response = httpx.Response(401, request=httpx.Request("POST", "http://test"))
        self.mock_client.post.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=response.request, response=response,
        )
        with pytest.raises(DuffelServiceError, match="misconfigured"):
            await search_flights(simple_query)

    async def test_422_raises_invalid_params(self, simple_query):
        response = httpx.Response(422, request=httpx.Request("POST", "http://test"))
        self.mock_client.post.side_effect = httpx.HTTPStatusError(
            "Unprocessable", request=response.request, response=response,
        )
        with pytest.raises(DuffelServiceError, match="Invalid search parameters"):
            await search_flights(simple_query)

    async def test_500_raises_unavailable(self, simple_query):
        response = httpx.Response(500, request=httpx.Request("POST", "http://test"))
        self.mock_client.post.side_effect = httpx.HTTPStatusError(
            "Server Error", request=response.request, response=response,
        )
        with pytest.raises(DuffelServiceError, match="unavailable"):
            await search_flights(simple_query)

    async def test_connection_error_raises_unavailable(self, simple_query):
        self.mock_client.post.side_effect = httpx.ConnectError("connection refused")
        with pytest.raises(DuffelServiceError, match="unavailable"):
            await search_flights(simple_query)

    async def test_error_type_is_search_error(self, simple_query):
        self.mock_client.post.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(DuffelServiceError) as exc_info:
            await search_flights(simple_query)
        assert exc_info.value.error_type == "search_error"
        assert exc_info.value.status_code == 502
