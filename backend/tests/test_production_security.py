from datetime import timedelta
from pathlib import Path
from secrets import token_urlsafe

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.auth import digest
from app.core.config import Settings, settings
from app.main import app
from app.models.entities import AuthSession, RegistrationInvitation
from app.services.activity import now_utc

ORIGIN = "https://learn.example.org"
PASSWORD = "A synthetic regression test password!"


def production_settings(**overrides):
    return Settings(
        _env_file=None,
        **{
            "APP_ENV": "production",
            "AUTH_MODE": "accounts",
            "COOKIE_SECURE": True,
            "PUBLIC_ORIGIN": ORIGIN,
            "CORS_ORIGINS": [],
            "AUTH_RATE_SECRET": token_urlsafe(32),
            "INIT_DB_ON_STARTUP": False,
            "TESTING": False,
            "USE_MOCK_MODELS": False,
            "DATABASE_URL": f"postgresql+psycopg://owner:{token_urlsafe(24)}@postgres/bhashabridge",
            **overrides,
        },
    )


@pytest.mark.parametrize(
    "unsafe",
    [
        {"DATABASE_URL": "sqlite:///:memory:"},
        {"TESTING": True},
        {"USE_MOCK_MODELS": True},
        {"INIT_DB_ON_STARTUP": True},
        {"COOKIE_SECURE": False},
        {"CORS_ORIGINS": ["*"]},
        {"PUBLIC_ORIGIN": "http://learn.example.org"},
        {"AUTH_RATE_SECRET": "bad"},
        {"TRUSTED_PROXY": "172.31.0.0/16"},
    ],
)
def test_production_configuration_rejects_unsafe_values(unsafe):
    with pytest.raises(ValueError):
        production_settings(**unsafe)


def test_production_configuration_accepts_private_postgres():
    assert production_settings().invitation_required


def test_invite_origin_rotation_expiry_and_role(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setattr(settings, "AUTH_MODE", "accounts")
    monkeypatch.setattr(settings, "COOKIE_SECURE", True)
    token = token_urlsafe(32)
    db_session.add(
        RegistrationInvitation(
            token_hash=digest(token),
            username="invited_learner",
            expires_at=now_utc() + timedelta(hours=24),
        )
    )
    db_session.commit()
    browser = TestClient(app, base_url=ORIGIN)
    credentials = {"username": "invited_learner", "password": PASSWORD}
    invited = {**credentials, "invitation_token": token, "role": "reviewer"}
    assert client.get("/api/auth/config").status_code == 400
    assert browser.post("/api/auth/register", json=invited).status_code == 403
    browser.headers["Origin"] = ORIGIN
    assert browser.post("/api/auth/register", json=credentials).status_code == 403
    assert (
        browser.post(
            "/api/auth/register", json={**invited, "username": "different"}
        ).status_code
        == 403
    )
    created = browser.post("/api/auth/register", json=invited)
    assert created.status_code == 201 and created.json()["role"] == "learner"
    assert "httponly" in created.headers.get_list("set-cookie")[0].lower()
    assert browser.post("/api/auth/register", json=invited).status_code == 403
    old = browser.cookies.get("bb_session")
    old_csrf = browser.cookies.get("bb_csrf")
    assert browser.post("/api/auth/login", json=credentials).status_code == 200
    assert browser.cookies.get("bb_session") != old
    assert browser.cookies.get("bb_csrf") != old_csrf
    forged = TestClient(app, base_url=ORIGIN, headers={"Cookie": f"bb_session={old}"})
    assert forged.get("/api/auth/me").status_code == 401
    assert (
        browser.post(
            "/api/progress/bridge-mode",
            json={"mode": "beginner"},
            headers={"X-CSRF-Token": old_csrf},
        ).status_code
        == 403
    )
    current = digest(browser.cookies.get("bb_session"))
    db_session.execute(
        update(AuthSession)
        .where(AuthSession.token_hash == current)
        .values(expires_at=now_utc() - timedelta(seconds=1))
    )
    db_session.commit()
    assert browser.get("/api/auth/me").status_code == 401


def test_validation_and_request_limits_are_text_free(client, caplog):
    secret = "private-credential-value"
    response = client.post(
        "/api/auth/login", json={"username": "bad name", "password": secret}
    )
    assert response.status_code == 422
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert secret not in response.text and secret not in caplog.text
    oversized = client.post(
        "/api/auth/login", content=b"x" * (settings.MAX_REQUEST_BYTES + 1)
    )
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "body_too_large"


def test_local_explanation_cannot_call_provider(client, monkeypatch):
    from app.services.explanation.llm_tutor import llm_tutor

    monkeypatch.setattr(settings, "TRANSLATION_MODE", "local")
    monkeypatch.setattr(
        llm_tutor,
        "explain",
        lambda *args, **kwargs: pytest.fail("Cloud explain was called"),
    )
    response = client.post(
        "/api/explain",
        json={
            "source_text": "मुझे पानी चाहिए",
            "source_language": "hindi",
            "target_text": "मला पाणी पाहिजे",
            "target_language": "marathi",
            "translation_mode": "hybrid",
        },
    )
    assert (
        response.status_code == 200
        and response.json()["explanation_source"] == "local_rules"
    )


def test_model_manifest_checks_code_and_weight_identity(tmp_path, monkeypatch):
    import json

    from app.services.translation.model_snapshot import model_snapshot, sha256

    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    weight = snapshot / "test.safetensors"
    weight.write_bytes(b"manifest-fixture")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "models": {
                    "author/model": {
                        "directory": "snapshot",
                        "revision": "a" * 40,
                        "sha256": {weight.name: sha256(weight)},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "MODEL_MANIFEST", manifest)
    monkeypatch.setattr(settings, "MODEL_MANIFEST_SHA256", sha256(manifest))
    assert model_snapshot("author/model") == (
        str(Path(snapshot)),
        "a" * 40,
        {"local_files_only": True},
    )
    weight.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        model_snapshot("author/model")
