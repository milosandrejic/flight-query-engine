from datetime import date

from openai import AsyncOpenAI

from src.flight_query_engine.config import settings
from src.flight_query_engine.schemas.flight_search import ParsedFlightQuery

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = f"""\
Extract flight search parameters from natural language queries.

Rules:
- Use 3-letter IATA airport codes (BEG=Belgrade, DXB=Dubai, JFK=New York, LHR=London)
- Use 2-letter IATA airline codes (FZ=Fly Dubai, EK=Emirates, BA=British Airways)
- Dates in YYYY-MM-DD format
- If trip duration specified (e.g. "7 days"), set trip_duration_days and calculate return_date
- Set baggage_only=true if: "no checked bags", "cabin baggage only", "without checked baggage"
- Set baggage_only=false if: "with checked bags", "luggage included"
- Set baggage_only=null if not mentioned
- Set sort_by="price" if: "cheap", "cheapest", "lowest price", "budget"
- Set sort_by="duration" if: "fast", "fastest", "quickest", "shortest"
- Set sort_by=null if not mentioned
- Default: 1 adult, economy class
- Dates relative to: {date.today().isoformat()}

Examples:
- "Belgrade to Dubai in February 7 days 2 persons without checked baggage with Fly Dubai"
  → origin: "BEG", destination: "DXB", departure_date: "2026-02-01", \
trip_duration_days: 7, return_date: "2026-02-08", \
passengers: {{adults: 2}}, airlines: ["FZ"], baggage_only: true
- "Cheapest flight NYC to London" → origin: "JFK", destination: "LHR", sort_by: "price"
- "Fastest direct flight Paris to Tokyo" → origin: "CDG", destination: "NRT", \
max_stops: 0, sort_by: "duration"
- "tomorrow" → +1 day from today
- "next week" → +7 days from today\
"""


async def parse_flight_query(user_query: str) -> ParsedFlightQuery:
    """Parse natural language into structured flight search params.

    Uses OpenAI structured outputs — the SDK enforces the Pydantic schema
    so we get a validated ParsedFlightQuery back directly, no JSON parsing.
    """
    completion = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
        response_format=ParsedFlightQuery,
    )
    result = completion.choices[0].message.parsed
    if result is None:
        msg = "OpenAI returned empty parsed result"
        raise ValueError(msg)
    return result
