from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.flight_query_engine.exceptions import DuffelServiceError, OfferNotFoundError
from src.flight_query_engine.services.duffel_service import (
    _parse_condition,
    _transform_offer_details,
    get_offer,
)

MOCK_FULL_OFFER = {
    "id": "off_123",
    "total_amount": "450.00",
    "base_amount": "409.20",
    "tax_amount": "40.80",
    "total_currency": "GBP",
    "expires_at": "2026-07-01T12:00:00Z",
    "total_emissions_kg": "460",
    "owner": {"name": "British Airways"},
    "conditions": {
        "change_before_departure": {
            "allowed": True,
            "penalty_amount": "50.00",
            "penalty_currency": "GBP",
        },
        "refund_before_departure": {
            "allowed": False,
            "penalty_amount": None,
            "penalty_currency": None,
        },
    },
    "slices": [
        {
            "origin": {"iata_code": "JFK"},
            "destination": {"iata_code": "LHR"},
            "duration": "PT7H00M",
            "segments": [
                {
                    "origin": {"iata_code": "JFK"},
                    "destination": {"iata_code": "LHR"},
                    "departing_at": "2026-06-15T10:00:00",
                    "arriving_at": "2026-06-15T22:00:00",
                    "marketing_carrier": {"iata_code": "BA", "name": "British Airways"},
                    "marketing_carrier_flight_number": "178",
                    "duration": "PT7H00M",
                    "aircraft": {"name": "Boeing 777-200"},
                },
            ],
        },
    ],
    "passengers": [
        {
            "id": "pas_001",
            "type": "adult",
            "baggages": [
                {"type": "carry_on", "quantity": 1},
                {"type": "checked", "quantity": 1},
            ],
        },
    ],
}


class TestParseCondition:
    def test_none_returns_none(self):
        assert _parse_condition(None) is None

    def test_allowed_with_penalty(self):
        cond = _parse_condition({
            "allowed": True,
            "penalty_amount": "50.00",
            "penalty_currency": "GBP",
        })
        assert cond.allowed is True
        assert cond.penalty_amount == "50.00"
        assert cond.penalty_currency == "GBP"

    def test_not_allowed(self):
        cond = _parse_condition({"allowed": False})
        assert cond.allowed is False
        assert cond.penalty_amount is None


class TestTransformOfferDetails:
    def test_price_breakdown(self):
        result = _transform_offer_details(MOCK_FULL_OFFER)
        assert result.price.total == 450.0
        assert result.price.base == 409.20
        assert result.price.tax == 40.80
        assert result.price.currency == "GBP"

    def test_conditions(self):
        result = _transform_offer_details(MOCK_FULL_OFFER)
        assert result.conditions.change_before_departure.allowed is True
        assert result.conditions.change_before_departure.penalty_amount == "50.00"
        assert result.conditions.refund_before_departure.allowed is False

    def test_slices_and_segments(self):
        result = _transform_offer_details(MOCK_FULL_OFFER)
        assert len(result.slices) == 1
        s = result.slices[0]
        assert s.origin == "JFK"
        assert s.destination == "LHR"
        assert s.duration == "PT7H00M"
        assert len(s.segments) == 1
        seg = s.segments[0]
        assert seg.carrier == "BA"
        assert seg.carrier_name == "British Airways"
        assert seg.flight_number == "178"
        assert seg.aircraft == "Boeing 777-200"

    def test_passengers_with_baggage(self):
        result = _transform_offer_details(MOCK_FULL_OFFER)
        assert len(result.passengers) == 1
        p = result.passengers[0]
        assert p.id == "pas_001"
        assert p.type == "adult"
        assert len(p.baggages) == 2
        assert p.baggages[0].type == "carry_on"
        assert p.baggages[1].type == "checked"

    def test_metadata_fields(self):
        result = _transform_offer_details(MOCK_FULL_OFFER)
        assert result.expires_at == "2026-07-01T12:00:00Z"
        assert result.total_emissions_kg == "460"
        assert result.owner_name == "British Airways"

    def test_no_tax(self):
        offer = {**MOCK_FULL_OFFER, "tax_amount": None}
        result = _transform_offer_details(offer)
        assert result.price.tax is None

    def test_no_aircraft(self):
        offer = {**MOCK_FULL_OFFER}
        offer["slices"] = [
            {
                **MOCK_FULL_OFFER["slices"][0],
                "segments": [
                    {**MOCK_FULL_OFFER["slices"][0]["segments"][0], "aircraft": None},
                ],
            },
        ]
        result = _transform_offer_details(offer)
        assert result.slices[0].segments[0].aircraft is None


class TestGetOfferErrors:
    async def test_timeout_raises(self):
        with patch(
            "src.flight_query_engine.services.duffel_service.httpx.AsyncClient",
        ) as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(DuffelServiceError, match="timed out"):
                await get_offer("off_123")

    async def test_404_raises_offer_not_found(self):
        with patch(
            "src.flight_query_engine.services.duffel_service.httpx.AsyncClient",
        ) as mock_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_resp,
            )
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(OfferNotFoundError):
                await get_offer("off_nonexistent")

    async def test_401_raises_misconfigured(self):
        with patch(
            "src.flight_query_engine.services.duffel_service.httpx.AsyncClient",
        ) as mock_cls:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_resp,
            )
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(DuffelServiceError, match="misconfigured"):
                await get_offer("off_123")

    async def test_connection_error_raises(self):
        with patch(
            "src.flight_query_engine.services.duffel_service.httpx.AsyncClient",
        ) as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(DuffelServiceError, match="unavailable"):
                await get_offer("off_123")
