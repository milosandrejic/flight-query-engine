import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

# --- Enums ---

class CabinClass(StrEnum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"

class SortBy(StrEnum):
    PRICE = "price"
    DURATION = "duration"

# --- Request ---

class FlightSearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=500, description="Natural language flight search query",
    )
    user_id: uuid.UUID | None = Field(
        None, description="Optional user identifier for search history",
    )


# --- Parsed query (returned by OpenAI structured output) ---


class Passengers(BaseModel):
    adults: int = Field(1, ge=1)
    children: int = Field(0, ge=0)
    infants: int = Field(0, ge=0)


class ParsedFlightQuery(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3, description="IATA airport code")
    destination: str = Field(..., min_length=3, max_length=3, description="IATA airport code")
    departure_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    return_date: str | None = None
    trip_duration_days: int | None = None
    passengers: Passengers = Field(default_factory=Passengers)
    cabin_class: CabinClass = CabinClass.ECONOMY
    max_stops: int | None = None
    airlines: list[str] | None = None
    baggage_only: bool | None = None
    sort_by: SortBy | None = None


# --- Flight result ---


class Price(BaseModel):
    amount: float
    currency: str


class FlightSegment(BaseModel):
    origin: str
    destination: str
    departing_at: str
    arriving_at: str
    carrier: str
    flight_number: str
    duration: str | None = None


class FlightResult(BaseModel):
    id: str
    price: Price
    segments: list[FlightSegment]
    total_duration: int
    stops: int


# --- Response ---


class SearchMetadata(BaseModel):
    search_id: uuid.UUID
    results_count: int
    search_time_ms: int
    timestamp: str


class FlightSearchResponse(BaseModel):
    parsed_query: ParsedFlightQuery
    results: list[FlightResult]
    metadata: SearchMetadata
