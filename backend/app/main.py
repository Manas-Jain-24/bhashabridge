from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.database import engine, Base, SessionLocal
import app.models.entities # ensures models are registered
from app.models.seed import seed_database

# Create database tables and seed defaults
Base.metadata.create_all(bind=engine)
with SessionLocal() as db_session:
    seed_database(db_session)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="NLP-powered Hindi–Marathi language-learning backend with Roman-Devanagari bridge."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import analyze, translate, transliterate, explain, practice, progress, gamification

app.include_router(analyze.router, prefix="/api", tags=["Analysis & Learning"])
app.include_router(translate.router, prefix="/api", tags=["Translation"])
app.include_router(transliterate.router, prefix="/api", tags=["Transliteration"])
app.include_router(explain.router, prefix="/api", tags=["Explanations"])
app.include_router(practice.router, prefix="/api", tags=["Practice Engine"])
app.include_router(progress.router, prefix="/api", tags=["Learner Progress"])
app.include_router(gamification.router, prefix="/api", tags=["Gamification Hub"])

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "database": "sqlite_ready"
    }
