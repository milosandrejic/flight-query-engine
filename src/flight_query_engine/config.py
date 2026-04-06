from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "flight_query_engine"

    # External APIs
    openai_api_key: str = ""
    duffel_api_key: str = ""

    # Application
    app_env: str = "development"
    port: int = 8000
    log_level: str = Field(default="info")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

settings = Settings()
