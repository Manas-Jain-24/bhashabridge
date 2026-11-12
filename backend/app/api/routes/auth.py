from datetime import timedelta
from typing import Annotated
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, StringConstraints
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.auth import current_user, check_origin, hash_password, verify_password, new_session, digest, Identity
from app.core.config import settings
from app.models.database import get_db
from app.models.entities import (User, AccountCredential, AuthSession, LanguageProfile,
                                 UserGamification, Progress, Milestone)
from app.services.activity import now_utc
from app.services.limits import reserve

router = APIRouter(prefix='/auth')


class Credentials(BaseModel):
    username: Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9_]{3,40}$')]
    password: Annotated[str, StringConstraints(min_length=12, max_length=128)]


def throttle(request, db):
    check_origin(request)
    minute = int(now_utc().timestamp()) // 300
    client = request.client.host if request.client else 'unknown'
    if not reserve(db, f'auth:{digest(client)}:{minute}', 20, now_utc()+timedelta(minutes=10)):
        db.rollback()
        raise HTTPException(429, 'Too many authentication attempts. Retry later.', headers={'Retry-After':'300'})
    db.commit()


@router.get('/config')
def config():
    return {'mode':settings.AUTH_MODE, 'registration':settings.ALLOW_REGISTRATION}


@router.get('/me')
def me(user: Identity = Depends(current_user)):
    return {'id':user.id, 'username':user.username, 'role':user.role}


@router.post('/register', status_code=201)
def register(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    throttle(request, db)
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(403, 'Registration is disabled')
    username = body.username.lower()
    encoded = hash_password(body.password)
    try:
        user = User(username=username)
        db.add(user); db.flush()
        db.add(AccountCredential(user_id=user.id, password_hash=encoded, role='learner'))
        db.add(LanguageProfile(user_id=user.id))
        db.add(UserGamification(user_id=user.id))
        milestone = db.query(Milestone).order_by(Milestone.level).first()
        if milestone:
            db.add(Progress(user_id=user.id, milestone_id=milestone.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Choose another username')
    new_session(db, user.id, response)
    return {'id':user.id, 'username':user.username, 'role':'learner'}


@router.post('/login')
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    throttle(request, db)
    user = db.query(User).filter_by(username=body.username.lower()).first()
    credential = db.get(AccountCredential, user.id) if user else None
    if not credential:
        hash_password(body.password, '00'*16)  # comparable work for unknown usernames
        raise HTTPException(401, 'Invalid username or password')
    if not verify_password(body.password, credential.password_hash):
        raise HTTPException(401, 'Invalid username or password')
    old = request.cookies.get('bb_session')
    if old:
        db.query(AuthSession).filter_by(token_hash=digest(old)).delete()
    new_session(db, user.id, response)
    return {'id':user.id, 'username':user.username, 'role':credential.role}


@router.post('/logout')
def logout(response: Response, user: Identity = Depends(current_user), db: Session = Depends(get_db)):
    if user.session_hash:
        db.query(AuthSession).filter_by(token_hash=user.session_hash).delete(); db.commit()
    response.delete_cookie('bb_session', path='/')
    response.delete_cookie('bb_csrf', path='/')
    return {'signed_out': True}


@router.get('/export')
def export_account(user: Identity = Depends(current_user), db: Session = Depends(get_db)):
    from app.models.database import Base
    from sqlalchemy import select
    from datetime import datetime
    data = {'account':{'username':user.username}, 'tables':{}}
    for table in Base.metadata.sorted_tables:
        if 'user_id' not in table.c or table.name in ('account_credentials','auth_sessions'):
            continue
        rows = db.execute(select(table).where(table.c.user_id == user.id)).mappings()
        data['tables'][table.name] = [{key:value.isoformat() if isinstance(value, datetime) else value
                                     for key,value in row.items()} for row in rows]
    # A private arcade snapshot contains answer keys; omit it from active exports.
    for row in data['tables'].get('arcade_sessions', []):
        row.pop('state_json', None)
    from app.models.entities import CorrectionReport, CorrectionEvent
    report_ids = select(CorrectionReport.id).where(CorrectionReport.user_id == user.id)
    data['tables']['correction_events'] = [
        {'id':row.id, 'report_id':row.report_id, 'actor_id':row.actor_id, 'action':row.action,
         'created_at':row.created_at.isoformat(), 'snapshot_json':row.snapshot_json}
        for row in db.query(CorrectionEvent).filter(CorrectionEvent.report_id.in_(report_ids))]
    return data


class DeleteAccount(BaseModel):
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


@router.delete('/account')
def delete_account(body: DeleteAccount, response: Response, user: Identity = Depends(current_user), db: Session = Depends(get_db)):
    from sqlalchemy import delete, select
    from app.models.database import Base
    from app.models.entities import CorrectionReport, CorrectionEvent
    if user.role == 'local':
        raise HTTPException(403, 'The local demo profile cannot be deleted through account controls')
    credential = db.get(AccountCredential, user.id)
    if not credential or not verify_password(body.password, credential.password_hash):
        raise HTTPException(401, 'Incorrect password')
    ids = select(CorrectionReport.id).where(CorrectionReport.user_id == user.id)
    db.execute(delete(CorrectionEvent).where(CorrectionEvent.report_id.in_(ids)))
    for table in reversed(Base.metadata.sorted_tables):
        if 'user_id' in table.c:
            db.execute(delete(table).where(table.c.user_id == user.id))
    # Keep only an anonymous actor row for other people's review audit records.
    db.get(User, user.id).username = 'deleted_' + secrets.token_hex(12)
    db.commit()
    response.delete_cookie('bb_session', path='/'); response.delete_cookie('bb_csrf', path='/')
    return {'deleted':True}
