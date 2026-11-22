"""PostgreSQL checks using an isolated schema inside the configured test database."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.database import Base
from app.models.entities import User
from app.models.migrations import is_current, migrate
from app.services.activity import now_utc
from app.services.limits import reserve


@pytest.fixture
def postgres():
    url = os.getenv("BB_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set BB_TEST_POSTGRES_URL to a disposable PostgreSQL database")
    control = create_engine(url, hide_parameters=True)
    if control.dialect.name != "postgresql":
        pytest.fail("BB_TEST_POSTGRES_URL must point to PostgreSQL")
    schema = "bb_test_" + uuid4().hex
    with control.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    engine = create_engine(
        url,
        connect_args={"options": f"-c search_path={schema}"},
        hide_parameters=True,
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with control.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        control.dispose()


@pytest.mark.parametrize("legacy_version", [0, 1])
def test_upgrade_retains_rows_and_aligns_user_sequence(postgres, legacy_version):
    with postgres.begin() as connection:
        if legacy_version == 1:
            Base.metadata.create_all(connection)
            connection.execute(text("DROP TABLE registration_invitations"))
            connection.execute(
                text("ALTER TABLE correction_reports DROP COLUMN publication_consent")
            )
            connection.execute(
                text("CREATE TABLE schema_versions (version INTEGER PRIMARY KEY)")
            )
            connection.execute(text("INSERT INTO schema_versions VALUES (1)"))
        else:
            connection.execute(
                text(
                    "CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(100) NOT NULL, created_at TIMESTAMP)"
                )
            )
        connection.execute(
            text("INSERT INTO users (id, username) VALUES (42, 'legacy_learner')")
        )

    migrate(postgres)
    migrate(postgres)
    with Session(postgres) as session, session.begin():
        assert is_current(session.connection())
        assert session.get(User, 42).username == "legacy_learner"
        new_user = User(username="new_learner")
        session.add(new_user)
        session.flush()
        assert new_user.id > 42


def test_atomic_quota_under_concurrent_first_insert(postgres):
    migrate(postgres)

    def attempt(_):
        with Session(postgres) as session, session.begin():
            return reserve(
                session, "integration-test-key", 3, now_utc() + timedelta(minutes=1)
            )

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(attempt, range(20))) == 3


def test_account_and_first_review_transactions(postgres, monkeypatch):
    from secrets import token_urlsafe

    from fastapi.testclient import TestClient

    from app.core.auth import digest
    from app.core.config import settings
    from app.main import app
    from app.models.database import get_db
    from app.models.entities import RegistrationInvitation, VocabularyWord

    migrate(postgres)
    origin = "https://production.test"
    password = "Synthetic integration password!"
    tokens = {name: token_urlsafe(32) for name in ("learner_one", "learner_two")}
    with Session(postgres) as session, session.begin():
        for username, token in tokens.items():
            session.add(
                RegistrationInvitation(
                    token_hash=digest(token),
                    username=username,
                    expires_at=now_utc() + timedelta(hours=1),
                )
            )
        session.add(
            VocabularyWord(
                language="marathi",
                devanagari="पाणी",
                roman="paani",
                english_meaning="water",
            )
        )
        session.flush()
        word_id = session.query(VocabularyWord.id).scalar()

    def postgres_session():
        with Session(postgres) as session:
            yield session

    monkeypatch.setitem(app.dependency_overrides, get_db, postgres_session)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AUTH_MODE", "accounts")
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    monkeypatch.setattr(settings, "PUBLIC_ORIGIN", origin)
    browsers = {}
    for username, token in tokens.items():
        browser = TestClient(app, base_url=origin, headers={"Origin": origin})
        created = browser.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": password,
                "invitation_token": token,
            },
        )
        assert created.status_code == 201
        browser.headers["X-CSRF-Token"] = browser.cookies.get("bb_csrf")
        browsers[username] = browser

    learner = browsers["learner_one"]
    peer = browsers["learner_two"]
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = executor.map(
            lambda _: (
                learner.post(
                    f"/api/vocabulary/review/{word_id}", json={"rating": "good"}
                ).status_code
            ),
            range(2),
        )
        assert sorted(statuses) == [200, 409]
    assert peer.get("/api/vocabulary/review").json()[0]["repetition_count"] == 0
    assert learner.post("/api/auth/logout").status_code == 200
    assert learner.get("/api/auth/me").status_code == 401
