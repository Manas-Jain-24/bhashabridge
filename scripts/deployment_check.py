"""Read-only deployment readiness: no migrations, provider calls or secret output."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def check(settings,engine):
    from app.models.migrations import is_current
    findings=[]
    if settings.APP_ENV!='production':findings.append('APP_ENV must be production')
    if settings.AUTH_MODE!='accounts':findings.append('Account authentication required')
    if not settings.COOKIE_SECURE:findings.append('Secure cookies required behind HTTPS')
    if settings.TESTING or settings.USE_MOCK_MODELS:findings.append('Test/mock mode enabled')
    if settings.ALLOW_SQLITE_FALLBACK:findings.append('Database fallback enabled')
    if '*' in settings.CORS_ORIGINS:findings.append('Wildcard CORS enabled')
    if engine.dialect.name != "postgresql":findings.append("Production PostgreSQL is required")
    try:
        settings.production_requirements()
    except ValueError:
        findings.append("Production settings did not pass validation")
    try:
        with engine.connect() as connection:
            if not is_current(connection):
                findings.append('Database migration required')
    except Exception:findings.append('Database or schema unavailable')
    return {'configuration_ready':not findings,'findings':findings,
        'manual_deployment_checks':['HTTPS and same-origin proxy','Restore drill on staged database',
            'Production-sized load test','Provider billing cap','Review data retention and backup deletion'],
        'human_translation_quality_gate':'pending'}


if __name__=='__main__':
    from app.core.config import settings
    from app.models.database import engine
    result=check(settings,engine);print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['configuration_ready'] else 1)
