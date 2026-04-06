from datetime import datetime, timedelta

import httpx

from src.flight_query_engine.config import settings
from src.flight_query_engine.schemas.flight_search import (
    FlightResult,
    FlightSegment,
    ParsedFlightQuery,
    Price,
)

BASE_URL = "https://api.duffel.com"
MAX_RESULTS = 20
DEFAULT_CHILD_AGE = 10
DEFAULT_INFANT_AGE = 1


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.duffel_api_key}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _calculate_return_date(query: ParsedFlightQuery) -> str | None:
    if query.return_date:
        return query.return_date
    if query.trip_duration_days and query.departure_date:
        dep = datetime.strptime(query.departure_date, "%Y-%m-%d")
        return (dep + timedelta(days=query.trip_duration_days)).strftime("%Y-%m-%d")
    return None


def _build_passengers(query: ParsedFlightQuery) -> list[dict]:
    passengers: list[dict] = []
    for _ in range(query.passengers.adults):
        passengers.append({"type": "adult"})
    for _ in range(query.passengers.children):
        passengers.append({"age": DEFAULT_CHILD_AGE})
    for _ in range(query.passengers.infants):
        passengers.append({"age": DEFAULT_INFANT_AGE})
    return passengers or [{"type": "adult"}]


def _build_slices(query: ParsedFlightQuery, return_date: str | None) -> list[dict]:
    slices = [
        {
            "origin": query.origin,
            "destination": query.destination,
            "departure_date": query.departure_date,
        },
    ]
    if return_date:
        slices.append(
            {
                "origin": query.destination,
                "destination": query.origin,
                "departure_date": return_date,
            },
        )
    return slices


def _normalize_max_connections(max_stops: int | None) -> int | None:
    if max_stops is None:
        return None
    return min(2, max(0, max_stops))


def _parse_duration_minutes(iso_duration: str | None) -> int:
    """Parse ISO 8601 duration like 'PT2H30M' to minutes."""
    if not iso_duration:
        return 0
    hours = minutes = 0
    rest = iso_duration.replace("PT", "")
    if "H" in rest:
        h_part, rest = rest.split("H")
        hours = int(h_part)
    if "M" in rest:
        minutes = int(rest.replace("M", ""))
    return hours * 60 + minutes


def _transform_offer(offer: dict) -> FlightResult:
    total_duration = sum(
        _parse_duration_minutes(segment.get("duration"))
        for flight_slice in offer.get("slices", [])
        for segment in flight_slice.get("segments", [])
    )
    total_stops = sum(
        max(0, len(flight_slice.get("segments", [])) - 1)
        for flight_slice in offer.get("slices", [])
    )
    segments = [
        FlightSegment(
            origin=segment["origin"]["iata_code"],
            destination=segment["destination"]["iata_code"],
            departing_at=segment["departing_at"],
            arriving_at=segment["arriving_at"],
            carrier=segment.get("marketing_carrier", {}).get("iata_code", ""),
            flight_number=segment.get("marketing_carrier_flight_number", ""),
            duration=segment.get("duration"),
        )
        for flight_slice in offer.get("slices", [])
        for segment in flight_slice.get("segments", [])
    ]
    return FlightResult(
        id=offer["id"],
        price=Price(
            amount=float(offer["total_amount"]),
            currency=offer["total_currency"],
        ),
        segments=segments,
        total_duration=total_duration,
        stops=total_stops,
    )


async def search_flights(query: ParsedFlightQuery) -> list[FlightResult]:
    """Search flights via Duffel REST API."""
    return_date = _calculate_return_date(query)
    passengers = _build_passengers(query)
    slices = _build_slices(query, return_date)
    max_connections = _normalize_max_connections(query.max_stops)

    payload: dict = {
        "data": {
            "slices": slices,
            "passengers": passengers,
            "cabin_class": query.cabin_class,
        },
    }
    if max_connections is not None:
        payload["data"]["max_connections"] = max_connections

    async with httpx.AsyncClient(base_url=BASE_URL, headers=_headers()) as client:
        # 1. Create offer request
        resp = await client.post("/air/offer_requests", json=payload, timeout=30)
        resp.raise_for_status()
        offer_request = resp.json()["data"]

        # 2. List offers
        sort = "total_duration" if query.sort_by == "duration" else "total_amount"
        resp = await client.get(
            "/air/offers",
            params={"offer_request_id": offer_request["id"], "sort": sort},
            timeout=30,
        )
        resp.raise_for_status()
        offers = resp.json()["data"]

    # 3. Filter
    if query.airlines:
        codes = set(query.airlines)
        offers = [
            offer for offer in offers
            if any(
                segment.get("marketing_carrier", {}).get("iata_code") in codes
                or segment.get("operating_carrier", {}).get("iata_code") in codes
                for flight_slice in offer.get("slices", [])
                for segment in flight_slice.get("segments", [])
            )
        ]

    if query.baggage_only:
        offers = [
            offer for offer in offers
            if all(
                any(
                    baggage.get("type") == "carry_on"
                    for baggage in segment.get("passengers", [{}])[0].get("baggages", [])
                )
                for flight_slice in offer.get("slices", [])
                for segment in flight_slice.get("segments", [])
            )
        ]

    return [_transform_offer(offer) for offer in offers[:MAX_RESULTS]]
