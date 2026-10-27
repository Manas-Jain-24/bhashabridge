from pathlib import Path
import os
import json
from typing import Any, List, Optional, Union, Literal
from pydantic import field_validator
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
    TESTING: bool = False
    INIT_DB_ON_STARTUP: bool = True
    TRANSLATION_ENGINE: Literal["indictrans2", "modular", "m2m100"] = "indictrans2"
    ALLOW_SQLITE_FALLBACK: bool = False
    INDICTRANS2_MODEL_CHECKPOINT: str = "ai4bharat/indictrans2-indic-indic-dist-320M"
    HF_TOKEN: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
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

settings = Settings()
