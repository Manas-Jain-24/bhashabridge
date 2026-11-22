"""Create a single-use, username-bound production registration invitation."""

import argparse
import re
import secrets
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def issue(db, username: str, hours: int = 24) -> str:
    from app.core.auth import digest
    from app.models.entities import RegistrationInvitation, User
    from app.services.activity import now_utc

    username = username.lower()
    if not re.fullmatch(r"[a-z0-9_]{3,40}", username) or not 1 <= hours <= 168:
        raise ValueError("Provide a valid username and expiry between 1 and 168 hours")
    if db.query(User.id).filter_by(username=username).first():
        raise ValueError("Choose a username available for registration")
    token = secrets.token_urlsafe(32)
    db.add(
        RegistrationInvitation(
            token_hash=digest(token),
            username=username,
            expires_at=now_utc() + timedelta(hours=hours),
        )
    )
    db.commit()
    return token


def main():
    from app.models.database import SessionLocal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()
    with SessionLocal() as db:
        print(issue(db, args.username, args.hours))


if __name__ == "__main__":
    main()
