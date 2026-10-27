"""Shared reward ledger. Callers commit the event and learning changes together."""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.entities import LearningActivity, UserGamification


def now_utc():
    # SQLite round-trips naive timestamps; persist UTC consistently.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_profile(db: Session, user_id: int = 1):
    profile = db.query(UserGamification).filter_by(user_id=user_id).with_for_update().first()
    if profile is None:
        profile = UserGamification(user_id=user_id)
        db.add(profile)
        db.flush()
    return profile


def record_activity(db: Session, key: str, kind: str, xp: int = 0,
                    value: int = 1, user_id: int = 1, now=None) -> bool:
    profile = get_profile(db, user_id)
    if db.query(LearningActivity).filter_by(user_id=user_id, event_key=key).first():
        return False
    db.add(LearningActivity(user_id=user_id, event_key=key, kind=kind,
                            xp_awarded=xp, value=value, created_at=now or now_utc()))
    profile.xp = (profile.xp or 0) + xp
    profile.updated_at = now or now_utc()
    db.flush()
    return True


def current_streak(db: Session, user_id: int = 1, now=None):
    today = (now or now_utc()).date()
    dates = {row.created_at.date() for row in db.query(LearningActivity).filter(
        LearningActivity.user_id == user_id, LearningActivity.kind != "chest"
    ).all()}
    day = today if today in dates else today - timedelta(days=1)
    count = 0
    while day in dates:
        count += 1
        day -= timedelta(days=1)
    monday = today - timedelta(days=today.weekday())
    week = [{"day": (monday + timedelta(days=i)).strftime("%a"),
             "active": monday + timedelta(days=i) in dates,
             "today": monday + timedelta(days=i) == today} for i in range(7)]
    return count, week


def award_daily_missions(db: Session, user_id: int = 1, now=None):
    now = now or now_utc()
    db.flush()
    events = db.query(LearningActivity).filter(
        LearningActivity.user_id == user_id,
        LearningActivity.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)).all()
    completed = [
        ("m1", sum(e.kind == "review" for e in events) >= 5, 30),
        ("m2", any(e.kind == "blitz" and e.value >= 150 for e in events), 40),
        ("m3", any(e.kind == "speech" for e in events), 50),
    ]
    for mission, eligible, xp in completed:
        if eligible:
            record_activity(db, f"mission:{now.date()}:{mission}", "mission", xp, user_id=user_id, now=now)
