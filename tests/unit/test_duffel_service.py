from src.flight_query_engine.services.duffel_service import (
    _build_passengers,
    _build_slices,
    _calculate_return_date,
    _normalize_max_connections,
    _parse_duration_minutes,
    _transform_offer,
)
from tests.conftest import MOCK_DUFFEL_OFFER


class TestCalculateReturnDate:
    def test_explicit_return_date(self, simple_query):
        simple_query.return_date = "2026-06-22"
        assert _calculate_return_date(simple_query) == "2026-06-22"

    def test_from_trip_duration(self, duration_query):
        assert _calculate_return_date(duration_query) == "2026-02-08"

    def test_no_return(self, simple_query):
        assert _calculate_return_date(simple_query) is None

    def test_explicit_takes_priority_over_duration(self, duration_query):
        duration_query.return_date = "2026-03-01"
        assert _calculate_return_date(duration_query) == "2026-03-01"


class TestBuildPassengers:
    def test_single_adult(self, simple_query):
        result = _build_passengers(simple_query)
        assert result == [{"type": "adult"}]

    def test_mixed_passengers(self, return_query):
        result = _build_passengers(return_query)
        assert result == [
            {"type": "adult"},
            {"type": "adult"},
            {"age": 10},
            {"age": 1},
        ]


class TestBuildSlices:
    def test_one_way(self, simple_query):
        slices = _build_slices(simple_query, return_date=None)
        assert len(slices) == 1
        assert slices[0]["origin"] == "JFK"
        assert slices[0]["destination"] == "LHR"

    def test_round_trip(self, simple_query):
        slices = _build_slices(simple_query, return_date="2026-06-22")
        assert len(slices) == 2
        assert slices[1]["origin"] == "LHR"
        assert slices[1]["destination"] == "JFK"
        assert slices[1]["departure_date"] == "2026-06-22"


class TestNormalizeMaxConnections:
    def test_none_stays_none(self):
        assert _normalize_max_connections(None) is None

    def test_zero_is_direct(self):
        assert _normalize_max_connections(0) == 0

    def test_clamped_to_two(self):
        assert _normalize_max_connections(5) == 2

    def test_negative_clamped_to_zero(self):
        assert _normalize_max_connections(-1) == 0


class TestParseDurationMinutes:
    def test_hours_and_minutes(self):
        assert _parse_duration_minutes("PT2H30M") == 150

    def test_hours_only(self):
        assert _parse_duration_minutes("PT7H") == 420

    def test_minutes_only(self):
        assert _parse_duration_minutes("PT45M") == 45

    def test_none_returns_zero(self):
        assert _parse_duration_minutes(None) == 0

    def test_empty_string_returns_zero(self):
        assert _parse_duration_minutes("") == 0


class TestTransformOffer:
    def test_basic_transform(self):
        result = _transform_offer(MOCK_DUFFEL_OFFER)
        assert result.id == "off_123"
        assert result.price.amount == 450.00
        assert result.price.currency == "GBP"
        assert len(result.segments) == 1
        assert result.segments[0].origin == "JFK"
        assert result.segments[0].destination == "LHR"
        assert result.segments[0].carrier == "BA"
        assert result.segments[0].flight_number == "178"
        assert result.total_duration == 420
        assert result.stops == 0

    def test_multi_segment_offer(self):
        offer = {
            "id": "off_456",
            "total_amount": "300.00",
            "total_currency": "USD",
            "slices": [
                {
                    "segments": [
                        {
                            "origin": {"iata_code": "JFK"},
                            "destination": {"iata_code": "ORD"},
                            "departing_at": "2026-06-15T08:00:00",
                            "arriving_at": "2026-06-15T10:00:00",
                            "marketing_carrier": {"iata_code": "AA"},
                            "marketing_carrier_flight_number": "100",
                            "duration": "PT2H00M",
                        },
                        {
                            "origin": {"iata_code": "ORD"},
                            "destination": {"iata_code": "LHR"},
                            "departing_at": "2026-06-15T12:00:00",
                            "arriving_at": "2026-06-16T01:00:00",
                            "marketing_carrier": {"iata_code": "AA"},
                            "marketing_carrier_flight_number": "200",
                            "duration": "PT8H00M",
                        },
                    ],
                },
            ],
        }
        result = _transform_offer(offer)
        assert result.stops == 1
        assert result.total_duration == 600
        assert len(result.segments) == 2
