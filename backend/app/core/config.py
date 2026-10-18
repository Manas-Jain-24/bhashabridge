import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "BhashaBridge"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bhashabridge.db")
    USE_MOCK_MODELS: bool = os.getenv("USE_MOCK_MODELS", "true").lower() == "true"
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"
    )

settings = Settings()
