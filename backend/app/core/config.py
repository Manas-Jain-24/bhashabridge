from pathlib import Path
import os
import json
from typing import Any, List, Optional, Union, Literal
from pydantic import field_validator, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH: Path = PROJECT_ROOT / "bhashabridge.db"
DEFAULT_DATABASE_URL: str = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "BhashaBridge"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = DEFAULT_DATABASE_URL
    USE_MOCK_MODELS: bool = False
    BENGALI_NEURAL_TRANSLITERATION: bool = True
    TESTING: bool = False
    APP_ENV: Literal['development', 'test', 'production'] = 'development'
    AUTH_MODE: Literal['local', 'accounts'] = 'local'
    LOCAL_USER_ID: int = Field(1, ge=1)
    SESSION_HOURS: int = Field(24, ge=1, le=168)
    COOKIE_SECURE: bool = False
    ALLOW_REGISTRATION: bool = True
    REQUESTS_PER_MINUTE: int = Field(120, ge=1)
    CLOUD_CALLS_PER_DAY: int = Field(100, ge=0)
    CLOUD_USER_CALLS_PER_DAY: int = Field(25, ge=0)
    CLOUD_TOTAL_SCOPE: Optional[str] = None
    CLOUD_TOTAL_CALLS: int = Field(100, ge=0)
    REQUEST_TIMEOUT_SECONDS: float = Field(60, ge=1, le=180)
    INFERENCE_WORKERS: int = Field(2, ge=1, le=4)
    INIT_DB_ON_STARTUP: bool = True
    TRANSLATION_ENGINE: Literal["indictrans2", "modular", "m2m100"] = "indictrans2"
    TRANSLATION_MODE: Literal["local", "hybrid"] = "hybrid"
    ALLOW_SQLITE_FALLBACK: bool = False
    INDICTRANS2_MODEL_CHECKPOINT: str = "ai4bharat/indictrans2-indic-indic-dist-320M"
    INDICTRANS2_ADAPTER_DECISION: Optional[str] = None
    HF_TOKEN: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_TRANSLATION_MODEL: str = "gemini-3.5-flash"
    GEMINI_TRANSLATION_TIMEOUT_SECONDS: float = Field(30.0, ge=5, le=60)
    GEMINI_TIMEOUT_SECONDS: float = Field(15.0, ge=1, le=60)
    GEMINI_MAX_OUTPUT_TOKENS: int = Field(2048, ge=256, le=4096)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            origins = [orig.strip() for orig in v_clean.split(",") if orig.strip()]
            return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="allow"
    )

    @model_validator(mode='after')
    def production_requirements(self):
        if self.APP_ENV == 'production':
            if self.AUTH_MODE != 'accounts' or not self.COOKIE_SECURE:
                raise ValueError('Production requires account authentication and secure cookies')
            if self.ALLOW_SQLITE_FALLBACK or '*' in self.CORS_ORIGINS:
                raise ValueError('Production disallows database fallback and wildcard CORS')
        return self

settings = Settings()
