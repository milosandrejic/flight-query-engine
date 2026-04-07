from unittest.mock import AsyncMock, patch

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from src.flight_query_engine.exceptions import OpenAIServiceError
from src.flight_query_engine.services.openai_service import parse_flight_query


class TestParseFlightQueryErrors:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        self.mock_parse = AsyncMock()
        with patch(
            "src.flight_query_engine.services.openai_service.client.beta.chat.completions.parse",
            self.mock_parse,
        ):
            yield

    async def test_timeout_raises_parse_error(self):
        self.mock_parse.side_effect = APITimeoutError(request=None)
        with pytest.raises(OpenAIServiceError, match="timed out"):
            await parse_flight_query("NYC to London")

    async def test_rate_limit_raises_parse_error(self):
        self.mock_parse.side_effect = RateLimitError(
            message="rate limited",
            response=AsyncMock(status_code=429, headers={}),
            body=None,
        )
        with pytest.raises(OpenAIServiceError, match="busy"):
            await parse_flight_query("NYC to London")

    async def test_connection_error_raises_parse_error(self):
        self.mock_parse.side_effect = APIConnectionError(request=None)
        with pytest.raises(OpenAIServiceError, match="unavailable"):
            await parse_flight_query("NYC to London")

    async def test_unexpected_error_raises_parse_error(self):
        self.mock_parse.side_effect = RuntimeError("something broke")
        with pytest.raises(OpenAIServiceError, match="Failed to parse"):
            await parse_flight_query("NYC to London")

    async def test_null_result_raises_parse_error(self):
        mock_choice = AsyncMock()
        mock_choice.message.parsed = None
        self.mock_parse.return_value = AsyncMock(choices=[mock_choice])

        with pytest.raises(OpenAIServiceError, match="Could not understand"):
            await parse_flight_query("NYC to London")

    async def test_error_type_is_parse_error(self):
        self.mock_parse.side_effect = APITimeoutError(request=None)
        with pytest.raises(OpenAIServiceError) as exc_info:
            await parse_flight_query("NYC to London")
        assert exc_info.value.error_type == "parse_error"
        assert exc_info.value.status_code == 502
