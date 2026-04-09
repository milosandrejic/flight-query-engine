from unittest.mock import AsyncMock, patch

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from src.flight_query_engine.exceptions import OpenAIServiceError
from src.flight_query_engine.services.openai_service import parse_flight_query, parse_follow_up_query
from src.flight_query_engine.services.session_store import ConversationTurn
from src.flight_query_engine.schemas.flight_search import (
    CabinClass,
    ParsedFlightQuery,
    Passengers,
)


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


class TestParseFollowUpQuery:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        self.mock_parse = AsyncMock()
        with patch(
            "src.flight_query_engine.services.openai_service.client.beta.chat.completions.parse",
            self.mock_parse,
        ):
            yield

    @pytest.fixture()
    def prev_query(self):
        return ParsedFlightQuery(
            origin="JFK",
            destination="LHR",
            departure_date="2026-06-15",
            passengers=Passengers(adults=1),
            cabin_class=CabinClass.ECONOMY,
        )

    @pytest.fixture()
    def conversation_turns(self, prev_query):
        return [ConversationTurn(user_query="NYC to London June 15", parsed_query=prev_query)]

    async def test_builds_conversation_messages(self, conversation_turns, prev_query):
        mock_choice = AsyncMock()
        mock_choice.message.parsed = prev_query
        self.mock_parse.return_value = AsyncMock(choices=[mock_choice])

        await parse_follow_up_query(conversation_turns, "make it cheaper")

        call_kwargs = self.mock_parse.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "modifying a previous flight search" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "NYC to London June 15"
        assert messages[2]["role"] == "assistant"
        assert "JFK" in messages[2]["content"]
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "make it cheaper"

    async def test_returns_parsed_query(self, conversation_turns):
        modified_query = ParsedFlightQuery(
            origin="JFK",
            destination="LHR",
            departure_date="2026-06-15",
            passengers=Passengers(adults=1),
            cabin_class=CabinClass.ECONOMY,
            sort_by="price",
        )
        mock_choice = AsyncMock()
        mock_choice.message.parsed = modified_query
        self.mock_parse.return_value = AsyncMock(choices=[mock_choice])

        result = await parse_follow_up_query(conversation_turns, "make it cheaper")
        assert result.sort_by == "price"
        assert result.origin == "JFK"

    async def test_timeout_raises_parse_error(self, conversation_turns):
        self.mock_parse.side_effect = APITimeoutError(request=None)
        with pytest.raises(OpenAIServiceError, match="timed out"):
            await parse_follow_up_query(conversation_turns, "make it cheaper")

    async def test_null_result_raises(self, conversation_turns):
        mock_choice = AsyncMock()
        mock_choice.message.parsed = None
        self.mock_parse.return_value = AsyncMock(choices=[mock_choice])

        with pytest.raises(OpenAIServiceError, match="Could not understand"):
            await parse_follow_up_query(conversation_turns, "make it cheaper")
