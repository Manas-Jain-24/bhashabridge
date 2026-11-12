import sys
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.database import init_db, check_db_health
from app.services.transliteration.service import transliteration_service
from app.services.translation.indictrans2 import indictrans2_adapter
from app.services.explanation.llm_tutor import llm_tutor
from app.core.auth import current_user, Identity
from app.services.runtime import provider_status, metrics

logger = logging.getLogger("bhashabridge")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe startup: initialize tables and default seeds if needed
    skip_init = (
        getattr(app.state, "skip_init_db", False)
        or getattr(settings, "TESTING", False)
        or not getattr(settings, "INIT_DB_ON_STARTUP", True)
        or os.getenv("TESTING", "").lower() in ("true", "1")
        or "pytest" in sys.modules
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )
    if skip_init:
        logger.info("[*] Database startup initialization skipped (test/custom mode).")
    else:
        try:
            target_engine = getattr(app.state, "db_engine", None)
            init_db(target_engine=target_engine)
            logger.info("[*] BhashaBridge database initialization completed.")
        except Exception as exc:
            logger.error("Database startup initialization error (%s)", type(exc).__name__)
            raise exc
    yield
    # Graceful shutdown
    logger.info("[*] BhashaBridge application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="NLP-powered Hindi–Marathi language-learning backend with Roman-Devanagari bridge.",
    lifespan=lifespan
)

# CORS configuration: Wildcard '*' disables credentials to avoid browser rejection
has_wildcard_cors = any(origin == "*" for origin in settings.CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=not has_wildcard_cors,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import analyze, translate, transliterate, explain, practice, progress, gamification, auth, corrections

app.include_router(analyze.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Analysis & Learning"])
app.include_router(translate.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Translation"])
app.include_router(transliterate.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Transliteration"])
app.include_router(explain.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Explanations"])
app.include_router(practice.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Practice Engine"])
app.include_router(progress.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Learner Progress"])
app.include_router(gamification.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Gamification Hub"])
app.include_router(auth.router, prefix='/api', tags=['Accounts'])
app.include_router(corrections.router, prefix='/api', tags=['Corrections'])

@app.get("/api/health")
def health_check():
    target_engine = getattr(app.state, "db_engine", None)
    db_status = check_db_health(target_engine=target_engine)
    translit_neural = getattr(transliteration_service, "_is_loaded", False)
    trans_neural = getattr(indictrans2_adapter, "is_loaded", False)
    if trans_neural:
        translation_status = "indictrans2_neural"
    elif settings.TRANSLATION_ENGINE == "indictrans2" and not getattr(indictrans2_adapter, "_load_failed", False):
        translation_status = "indictrans2_not_loaded"
    else:
        translation_status = "curated_modular_fallback"
    llm_active = getattr(llm_tutor, "is_available", False)

    return {
        "status": "healthy" if db_status["status"] == "connected" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "provider": {"configured":bool(llm_active), **provider_status()},
        "database": {
            "status": db_status["status"],
            "type": db_status["type"]
        },
        "models": {
            "transliteration": "neural_seq2seq" if translit_neural else "rule_fallback",
            "translation": translation_status,
            "explanation_tutor": "gemini_sensei" if llm_active else "local_ud_rules"
        }
    }


@app.get("/api/languages")
def supported_languages():
    from app.core.languages import LANGUAGES
    return LANGUAGES


from app.api.routes import arcade
app.include_router(arcade.router, dependencies=[Depends(current_user)], prefix="/api", tags=["Multilingual Arcade"])


@app.get('/api/operations/metrics')
def runtime_metrics(user: Identity = Depends(current_user)):
    from fastapi import HTTPException
    if user.role not in ('local', 'reviewer'):
        raise HTTPException(403, 'Operations access is required')
    return metrics()
