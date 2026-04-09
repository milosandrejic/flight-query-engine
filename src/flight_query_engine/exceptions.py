class FlightQueryEngineError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, error_type: str = "server_error", status_code: int = 500):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        super().__init__(message)


class OpenAIServiceError(FlightQueryEngineError):
    """OpenAI API call failed."""

    def __init__(self, message: str = "Failed to parse flight query"):
        super().__init__(message, error_type="parse_error", status_code=502)


class DuffelServiceError(FlightQueryEngineError):
    """Duffel API call failed."""

    def __init__(self, message: str = "Failed to search flights"):
        super().__init__(message, error_type="search_error", status_code=502)


class ConfigError(FlightQueryEngineError):
    """Missing or invalid configuration."""

    def __init__(self, message: str = "Server misconfigured"):
        super().__init__(message, error_type="server_error", status_code=500)


class SessionNotFoundError(FlightQueryEngineError):
    """Requested session does not exist."""

    def __init__(self, message: str = "Session not found"):
        super().__init__(message, error_type="session_error", status_code=404)


class OfferNotFoundError(FlightQueryEngineError):
    """Requested offer does not exist or has expired."""

    def __init__(self, message: str = "Offer not found or expired"):
        super().__init__(message, error_type="offer_error", status_code=404)
