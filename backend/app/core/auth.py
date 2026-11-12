"""Opaque, revocable sessions and explicit local-development identity."""
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import hmac
import secrets
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.database import get_db
from app.models.entities import AccountCredential, AuthSession, User
from app.services.activity import now_utc


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**15, r=8, p=3, maxmem=64*1024*1024)
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
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or parsed.netloc != request.headers.get('host'):
            raise HTTPException(403, 'Use the same-origin application to submit changes')


def current_user(request: Request, db: Session = Depends(get_db)):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
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
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
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
    minute = int(now_utc().timestamp()) // 60
    if not reserve(db, f'request:{identity.id}:{minute}', settings.REQUESTS_PER_MINUTE,
                   now_utc()+timedelta(minutes=2)):
        db.rollback()
        raise HTTPException(429, 'Request limit reached. Retry shortly.', headers={'Retry-After':'60'})
    db.commit()
    return identity


def reviewer(user: Identity = Depends(current_user)):
    if user.role != 'reviewer':
        raise HTTPException(403, 'An explicitly assigned reviewer account is required')
    return user


def new_session(db, user_id, response):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expiry = now_utc() + timedelta(hours=settings.SESSION_HOURS)
    db.add(AuthSession(token_hash=digest(token), user_id=user_id, csrf_hash=digest(csrf), expires_at=expiry))
    db.commit()
    options = dict(secure=settings.COOKIE_SECURE, samesite='strict', path='/', max_age=settings.SESSION_HOURS*3600)
    response.set_cookie('bb_session', token, httponly=True, **options)
    response.set_cookie('bb_csrf', csrf, httponly=False, **options)
