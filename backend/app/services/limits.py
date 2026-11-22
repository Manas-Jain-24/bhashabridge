"""Database-backed quotas shared by processes; no user text is retained."""
from datetime import timedelta
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models.entities import UsageCounter
from app.services.activity import now_utc


def reserve(db, key, maximum, expires_at):
    if maximum <= 0:
        return False
    insert = postgres_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    statement = insert(UsageCounter).values(key=key, count=1, expires_at=expires_at)
    accepted = statement.on_conflict_do_update(
        index_elements=[UsageCounter.key],
        set_={"count": UsageCounter.count + 1},
        where=UsageCounter.count < maximum,
    ).returning(UsageCounter.count)
    return db.execute(accepted).scalar_one_or_none() is not None


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
