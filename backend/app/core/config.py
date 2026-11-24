from pathlib import Path
import json
import ipaddress
from typing import Any, List, Optional, Union, Literal
from urllib.parse import urlsplit
from pydantic import field_validator, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

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
    PUBLIC_ORIGIN: str = ""
    AUTH_RATE_SECRET: str = Field(default="", repr=False)
    TRUSTED_PROXY: str = ""
    AUTH_HASH_WORKERS: int = Field(2, ge=1, le=8)
    MAX_REQUEST_BYTES: int = Field(262144, ge=131072, le=1048576)
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
    MODEL_MANIFEST: Optional[Path] = None
    MODEL_MANIFEST_SHA256: str = ""
    TRANSLATION_CACHE_MAX_SIZE: int = Field(1000, ge=0, le=5000)
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
            return origins
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("MODEL_MANIFEST", mode="before")
    @classmethod
    def empty_manifest(cls, value):
        return value or None

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT.parent / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="allow",
        hide_input_in_errors=True,
    )

    @model_validator(mode='after')
    def production_requirements(self):
        if self.APP_ENV == 'production':
            if self.AUTH_MODE != 'accounts' or not self.COOKIE_SECURE:
                raise ValueError('Production requires account authentication and secure cookies')
            if self.ALLOW_SQLITE_FALLBACK or '*' in self.CORS_ORIGINS:
                raise ValueError('Production disallows database fallback and wildcard CORS')
            if self.TESTING or self.USE_MOCK_MODELS or self.INIT_DB_ON_STARTUP:
                raise ValueError('Production requires the migration command and real runtime settings')
            try:
                database = make_url(self.DATABASE_URL)
            except Exception:
                raise ValueError('Invalid production database URL') from None
            if (database.get_backend_name() != "postgresql" or not database.host
                    or not database.database or not database.username or not database.password
                    or database.password.lower() in {"password", "bhasha_pass", "changeme", "postgres"}):
                raise ValueError('Production requires explicitly configured PostgreSQL credentials')
            try:
                origin = urlsplit(self.PUBLIC_ORIGIN)
                port = origin.port
            except ValueError:
                raise ValueError('Invalid production origin') from None
            if (origin.scheme != 'https' or not origin.hostname or origin.username is not None
                    or origin.path or origin.query or origin.fragment
                    or self.PUBLIC_ORIGIN != f'https://{origin.netloc}'
                    or origin.netloc != origin.netloc.lower() or port == 443
                    or any(c.isspace() or c in "*\\" for c in origin.netloc)
                    or any(value != self.PUBLIC_ORIGIN for value in self.CORS_ORIGINS)):
                raise ValueError('Production requires a canonical, explicit HTTPS origin')
            if len(self.AUTH_RATE_SECRET) < 32 or len(set(self.AUTH_RATE_SECRET)) < 8:
                raise ValueError('Production requires a random AUTH_RATE_SECRET')
            if self.TRUSTED_PROXY:
                try:
                    ipaddress.ip_address(self.TRUSTED_PROXY)
                except ValueError:
                    raise ValueError('TRUSTED_PROXY must be one proxy IP address') from None
            if self.HF_TOKEN:
                raise ValueError('Provision neural models separately from the production application')
            if self.MODEL_MANIFEST and (len(self.MODEL_MANIFEST_SHA256) != 64
                    or any(char not in '0123456789abcdef' for char in self.MODEL_MANIFEST_SHA256)):
                raise ValueError('Production model manifests require a SHA-256 pin')
        return self

    @property
    def invitation_required(self) -> bool:
        return self.APP_ENV == "production"

settings = Settings()
