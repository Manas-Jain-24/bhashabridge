"""Opaque, revocable sessions and explicit local-development identity."""
from dataclasses import dataclass
from datetime import timedelta, timezone
import hashlib
import hmac
import secrets
from ipaddress import ip_address
from threading import BoundedSemaphore
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.database import get_db
from app.models.entities import AccountCredential, AuthSession, User
from app.services.activity import now_utc
from sqlalchemy import select

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
INFERENCE_ROUTES = {"/api/analyze", "/api/translate", "/api/transliterate", "/api/explain"}
_password_slots = BoundedSemaphore(settings.AUTH_HASH_WORKERS)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    if not _password_slots.acquire(blocking=False):
        raise HTTPException(503, "Authentication is busy. Retry shortly.", headers={"Retry-After": "2"})
    try:
        key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**15, r=8, p=3, maxmem=64*1024*1024)
    finally:
        _password_slots.release()
    return f'scrypt$32768$8$3${salt}${key.hex()}'


def verify_password(password, stored):
    try:
        _, n, r, p, salt, expected = stored.split('$')
        if (n, r, p) != ('32768', '8', '3'):
            return False
        return hmac.compare_digest(hash_password(password, salt), stored)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class Identity:
    id: int
    username: str
    role: str = 'learner'
    session_hash: str | None = None


def check_origin(request):
    origin = request.headers.get('origin')
    # Reject browser cross-site requests even if cookies were omitted (login CSRF).
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Cross-site requests are not allowed')
    if settings.APP_ENV == "production":
        if origin != settings.PUBLIC_ORIGIN:
            raise HTTPException(403, 'Use the same-origin application to submit changes')
        return
    if origin:
        try:
            parsed = urlsplit(origin)
        except ValueError:
            raise HTTPException(403, 'Invalid request origin') from None
        if parsed.scheme not in ('http', 'https') or parsed.netloc != request.headers.get('host'):
            raise HTTPException(403, 'Use the same-origin application to submit changes')


def client_address(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if settings.TRUSTED_PROXY and peer == settings.TRUSTED_PROXY:
        try:
            return str(ip_address(request.headers.get("x-forwarded-for", "")))
        except ValueError:
            return peer
    return peer


def lock_account(db: Session, user_id: int):
    if db.get_bind().dialect.name == "sqlite":
        # Start a write transaction before loading any mutable account state.
        # SQLite does not implement SELECT FOR UPDATE.
        from sqlalchemy import text
        database = db.connection()
        if not database.connection.driver_connection.in_transaction:
            database.execute(text("BEGIN IMMEDIATE"))
    return db.scalar(select(User).where(User.id == user_id).with_for_update())


def current_user(request: Request, db: Session = Depends(get_db)):
    mutating = request.method not in SAFE_METHODS
    if mutating:
        check_origin(request)
    token = request.cookies.get('bb_session')
    if token:
        session = db.get(AuthSession, digest(token))
        if not session or session.expires_at <= now_utc():
            raise HTTPException(401, 'Session expired. Sign in again.')
        user = db.get(User, session.user_id)
        credential = db.get(AccountCredential, session.user_id)
        if not user or not credential:
            raise HTTPException(401, 'Account is unavailable')
        if mutating:
            supplied = request.headers.get('x-csrf-token', '')
            if not hmac.compare_digest(digest(supplied), session.csrf_hash):
                raise HTTPException(403, 'Missing or invalid CSRF token')
        identity = Identity(user.id, user.username, credential.role, session.token_hash)
    elif settings.AUTH_MODE == 'local':
        host = urlsplit('http://'+request.headers.get('host','')).hostname
        if host not in ('127.0.0.1','localhost','::1') and not (settings.TESTING and host=='testserver'):
            raise HTTPException(403, 'Local mode requires a loopback hostname')
        if request.client and request.client.host not in ('127.0.0.1', '::1', 'localhost', 'testclient'):
            raise HTTPException(403, 'Local mode is restricted to loopback; enable account mode for deployment')
        user = db.get(User, settings.LOCAL_USER_ID)
        if not user:
            raise HTTPException(503, 'Local learner profile is not initialized')
        identity = Identity(user.id, user.username, 'local')
    else:
        raise HTTPException(401, 'Sign in to continue')
    request.state.identity = identity
    from app.services.limits import reserve
    minute = int(now_utc().replace(tzinfo=timezone.utc).timestamp()) // 60
    if not reserve(db, f'request:{identity.id}:{minute}', settings.REQUESTS_PER_MINUTE,
                   now_utc()+timedelta(minutes=2)):
        db.rollback()
        raise HTTPException(429, 'Request limit reached. Retry shortly.', headers={'Retry-After':'60'})
    db.commit()
    if mutating and identity.session_hash and request.url.path.rstrip("/") not in INFERENCE_ROUTES:
        # Recheck authorization after acquiring the same lock used for deletion
        # and session rotation. The route owns this transaction through commit.
        locked_user = lock_account(db, identity.id)
        session = db.get(AuthSession, identity.session_hash)
        credential = db.get(AccountCredential, identity.id)
        if not locked_user or not credential or not session or session.expires_at <= now_utc():
            raise HTTPException(401, "Session expired. Sign in again.")
        if credential.role != identity.role:
            identity = Identity(identity.id, identity.username, credential.role, identity.session_hash)
            request.state.identity = identity
    return identity


def reviewer(user: Identity = Depends(current_user)):
    if user.role != 'reviewer':
        raise HTTPException(403, 'An explicitly assigned reviewer account is required')
    return user


def stage_session(db, user_id):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expiry = now_utc() + timedelta(hours=settings.SESSION_HOURS)
    db.add(AuthSession(token_hash=digest(token), user_id=user_id, csrf_hash=digest(csrf), expires_at=expiry))
    return token, csrf


def set_session_cookies(response, token, csrf):
    options = dict(secure=settings.COOKIE_SECURE, samesite='strict', path='/', max_age=settings.SESSION_HOURS*3600)
    response.set_cookie('bb_session', token, httponly=True, **options)
    response.set_cookie('bb_csrf', csrf, httponly=False, **options)


def clear_session_cookies(response):
    options = dict(secure=settings.COOKIE_SECURE, samesite="strict", path="/")
    response.delete_cookie("bb_session", httponly=True, **options)
    response.delete_cookie("bb_csrf", **options)
