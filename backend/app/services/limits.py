"""Database-backed quotas shared by processes; no user text is retained."""
from datetime import timedelta
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from app.models.entities import UsageCounter
from app.services.activity import now_utc


def reserve(db, key, maximum, expires_at):
    if maximum <= 0:
        return False
    try:
        with db.begin_nested():
            db.add(UsageCounter(key=key, count=0, expires_at=expires_at))
            db.flush()
    except IntegrityError:
        pass
    return db.execute(update(UsageCounter).where(
        UsageCounter.key == key, UsageCounter.count < maximum
    ).values(count=UsageCounter.count + 1)).rowcount == 1


def reserve_cloud(db, user_id):
    from app.core.config import settings
    day = now_utc().date().isoformat()
    expiry = now_utc() + timedelta(days=2)
    accepted = (reserve(db, f'cloud:global:{day}', settings.CLOUD_CALLS_PER_DAY, expiry)
                and reserve(db, f'cloud:user:{user_id}:{day}', settings.CLOUD_USER_CALLS_PER_DAY, expiry))
    if accepted and settings.CLOUD_TOTAL_SCOPE:
        accepted = reserve(db, 'cloud:run:'+settings.CLOUD_TOTAL_SCOPE, settings.CLOUD_TOTAL_CALLS,
                           now_utc()+timedelta(days=3650))
    if accepted:
        db.commit()
    else:
        db.rollback()
    return accepted
