"""A review queue; submitted/model-generated proposals are never trusted memory."""
import json
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.orm import Session
from app.core.auth import current_user, reviewer, Identity
from app.core.languages import Language, InputText, check_source_script
from app.models.database import get_db
from app.models.entities import CorrectionReport, CorrectionEvent
from app.services.activity import now_utc

router = APIRouter(prefix='/corrections')
CATEGORIES = Literal['spelling', 'negation', 'tense', 'intent', 'entity', 'fluency', 'roman', 'english', 'explanation', 'other']


class Report(BaseModel):
    source_language: Language
    target_language: Language
    source_text: InputText
    observed_target: str = Field(max_length=4000)
    category: CATEGORIES
    purpose: Literal['runtime', 'evaluation'] = 'runtime'
    note: str = Field(default='', max_length=2000)
    provenance: str = Field(min_length=1, max_length=1000)
    license: str = Field(min_length=1, max_length=120)


class Proposal(BaseModel):
    version: int = Field(ge=1)
    target: str = Field(min_length=1, max_length=4000)
    roman: str = Field(default='', max_length=4000)
    english: str = Field(default='', max_length=1000)
    note: str = Field(min_length=1, max_length=2000)
    provenance: str | None = Field(default=None, min_length=1, max_length=1000)
    license: str | None = Field(default=None, min_length=1, max_length=120)


class Decision(BaseModel):
    version: int = Field(ge=1)
    status: Literal['reviewed', 'rejected']
    human_attestation: bool
    note: str = Field(min_length=1, max_length=2000)


def dto(row):
    return {column.name: (getattr(row, column.name).isoformat() if column.name.endswith('_at')
                         else getattr(row, column.name)) for column in row.__table__.columns}


def find(db, report_id, user):
    query = db.query(CorrectionReport).filter_by(id=report_id)
    if user.role != 'reviewer':
        query = query.filter_by(user_id=user.id)
    row = query.first()
    if not row:
        raise HTTPException(404, 'Report not found')
    return row


def event(db, row, user, action):
    db.flush()
    db.add(CorrectionEvent(report_id=row.id, actor_id=user.id, action=action,
                           snapshot_json=json.dumps(dto(row), ensure_ascii=False)))


def revise(db, row, version, values, user, action):
    changed = db.execute(update(CorrectionReport).where(
        CorrectionReport.id == row.id, CorrectionReport.version == version
    ).values(**values, version=version+1, updated_at=now_utc()))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'This report changed. Reload before editing.')
    db.refresh(row)
    event(db, row, user, action)
    db.commit()
    return dto(row)


@router.post('', status_code=201)
def report(body: Report, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    if body.source_language == body.target_language:
        raise HTTPException(422, 'Choose different languages')
    row = CorrectionReport(id=str(uuid.uuid4()), user_id=user.id, **body.model_dump())
    db.add(row); event(db, row, user, 'reported'); db.commit()
    return dto(row)


@router.get('')
def listing(db: Session = Depends(get_db), user: Identity = Depends(current_user),
            limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    query = db.query(CorrectionReport)
    if user.role != 'reviewer':
        query = query.filter_by(user_id=user.id)
    return [dto(row) for row in query.order_by(CorrectionReport.created_at.desc()).offset(offset).limit(limit)]


@router.get('/{report_id}/history')
def history(report_id: str, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    find(db, report_id, user)
    return [{'actor_id':row.actor_id, 'action':row.action, 'created_at':row.created_at.isoformat(),
             'snapshot':json.loads(row.snapshot_json)} for row in db.query(CorrectionEvent)
            .filter_by(report_id=report_id).order_by(CorrectionEvent.id)]


@router.put('/{report_id}/proposal')
def propose(report_id: str, body: Proposal, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    row = find(db, report_id, user)
    check_source_script(body.target, row.target_language)
    values = {'proposed_target':body.target, 'proposed_roman':body.roman,
        'proposed_english':body.english, 'note':body.note, 'status':'proposed'}
    for field in ('provenance','license'):
        if getattr(body,field) is not None:
            values[field] = getattr(body,field)
    return revise(db, row, body.version, values, user, 'proposed')


@router.post('/{report_id}/decision')
def decide(report_id: str, body: Decision, db: Session = Depends(get_db), user: Identity = Depends(reviewer)):
    row = find(db, report_id, user)
    if row.status != 'proposed' or not body.human_attestation:
        raise HTTPException(422, 'A proposal and explicit human review attestation are required')
    return revise(db, row, body.version, {'status':body.status, 'note':body.note}, user, body.status)
