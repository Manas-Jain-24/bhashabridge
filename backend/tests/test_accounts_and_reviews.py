import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.entities import AccountCredential, ArcadeSession, ReviewedTranslation, CorrectionReport


def register(client, username):
    response = client.post('/api/auth/register', json={'username':username, 'password':'A long test password 123!'})
    assert response.status_code == 201, response.text
    client.headers['X-CSRF-Token'] = client.cookies['bb_csrf']
    return response.json()


def test_account_sessions_and_csrf(client, monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_MODE', 'accounts')
    assert client.get('/api/progress').status_code == 401
    user = register(client, 'alice')
    assert client.get('/api/auth/me').json()['id'] == user['id']
    csrf = client.headers.pop('X-CSRF-Token')
    assert client.post('/api/progress/bridge-mode', json={'mode':'beginner'}).status_code == 403
    client.headers['X-CSRF-Token'] = csrf
    assert client.post('/api/progress/bridge-mode', json={'mode':'beginner'}).status_code == 200
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/progress').status_code == 401
    bad = client.post('/api/auth/login', json={'username':'alice', 'password':'incorrect password'})
    assert bad.status_code == 401


def test_two_users_cannot_access_sessions_reports_or_progress(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_MODE', 'accounts')
    alice = register(client, 'alice')
    started = client.post('/api/arcade/start', json={'language':'bengali','mode':'recognize','difficulty':'beginner'}).json()
    report = client.post('/api/corrections', json={
        'source_language':'hindi','target_language':'bengali','source_text':'नमस्ते',
        'observed_target':'নমস্কার', 'category':'other','provenance':'test authored', 'license':'CC0-1.0'}).json()
    other = TestClient(app)
    bob = register(other, 'bobby')
    assert bob['id'] != alice['id']
    assert other.get('/api/arcade/session/'+started['session_id']).status_code == 404
    assert other.post('/api/arcade/answer', json={'session_id':started['session_id'],
        'question_id':started['question']['id'],'choice_id':'a'}).status_code == 404
    assert other.get('/api/corrections').json() == []
    assert other.get('/api/corrections/'+report['id']+'/history').status_code == 404
    assert other.get('/api/practice/history').json() == []
    client.post('/api/progress/bridge-mode', json={'mode':'advanced'})
    assert other.get('/api/progress').json()['bridge_mode_level'] == 'intermediate'
    session = db_session.get(ArcadeSession, started['session_id'])
    private = json.loads(session.state_json)['questions'][0]
    answer = {'session_id':session.id,'question_id':private['id'],'choice_id':private['answer']}
    first = client.post('/api/arcade/answer', json=answer)
    again = client.post('/api/arcade/answer', json=answer)
    assert first.status_code == again.status_code == 200
    assert first.json()['feedback']['xp_awarded'] == 5
    assert again.json()['feedback']['xp_awarded'] == 0
    assert other.get('/api/arcade/stats/bengali').json()['xp'] == 0


def test_review_requires_role_attestation_and_version_without_promoting_memory(client, db_session):
    user = register(client, 'review_candidate')
    before = db_session.query(ReviewedTranslation).count()
    response = client.post('/api/corrections', json={
        'source_language':'hindi','target_language':'bengali','source_text':'मुझे पानी चाहिए',
        'observed_target':'পানি', 'category':'intent','provenance':'authored draft', 'license':'CC0-1.0'})
    assert response.status_code == 201
    row = response.json()
    proposal = {'version':1,'target':'আমার পানি চাই।','roman':'amar pani chai.',
                'english':'I want water.','note':'Draft, not reviewed.'}
    assert client.put('/api/corrections/'+row['id']+'/proposal', json=proposal).status_code == 200
    assert client.put('/api/corrections/'+row['id']+'/proposal', json=proposal).status_code == 409
    decision = {'version':2,'status':'reviewed','human_attestation':True,'note':'Test fixture only.'}
    assert client.post('/api/corrections/'+row['id']+'/decision', json=decision).status_code == 403
    credential = db_session.get(AccountCredential, user['id']); credential.role='reviewer'; db_session.commit()
    assert client.post('/api/corrections/'+row['id']+'/decision', json={**decision,'human_attestation':False}).status_code == 422
    assert client.post('/api/corrections/'+row['id']+'/decision', json=decision).status_code == 200
    assert len(client.get('/api/corrections/'+row['id']+'/history').json()) == 3
    assert db_session.query(ReviewedTranslation).count() == before


def test_cross_origin_and_public_limits(client, monkeypatch):
    assert client.post('/api/auth/login', headers={'Origin':'https://untrusted.example'},
        json={'username':'alice','password':'A long test password!'}).status_code == 403
    monkeypatch.setattr(settings, 'REQUESTS_PER_MINUTE', 1)
    assert client.get('/api/progress').status_code == 200
    assert client.get('/api/progress').status_code == 429


def test_cloud_budget_is_durable_and_never_exceeds_global_limit(db_session, monkeypatch):
    from app.services.limits import reserve_cloud
    monkeypatch.setattr(settings, 'CLOUD_CALLS_PER_DAY', 2)
    monkeypatch.setattr(settings, 'CLOUD_USER_CALLS_PER_DAY', 1)
    assert reserve_cloud(db_session, 1)
    assert not reserve_cloud(db_session, 1)
    assert reserve_cloud(db_session, 2)
    assert not reserve_cloud(db_session, 3)
