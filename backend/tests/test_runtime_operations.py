import asyncio
import importlib.util
import json
from pathlib import Path
import sqlite3
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from app.core.config import settings, Settings
from app.models.migrations import migrate
from app.services import runtime
from app.models.entities import User, AccountCredential, AuthSession, CorrectionReport

ROOT=Path(__file__).resolve().parents[2]


def script(name):
    import sys
    if str(ROOT/'scripts') not in sys.path: sys.path.insert(0,str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_frozen_matrix_has_600_requests_and_no_family_leakage():
    manifest,rows=script('runtime_evaluation').load_cases()
    assert manifest['native_and_roman_requests']==600
    assert len(rows)==300 and all(row['review_status']=='draft' for row in rows)
    assert len({row['intent_id'] for row in rows})==50


def test_draft_report_cannot_promote_a_model():
    value={'complete':True,'protocol':{'cases_sha256':'same'},'attempts':[
        {'id':'case','path':'roman_local','split':'test','source_language':'hindi','target_language':'bengali',
         'result':{},'protected_values_preserved':True}], 'summary':{}}
    decision=script('check_runtime_promotion').evaluate(value,value)
    assert not decision['promote'] and 'independent_human_review_required' in decision['reasons']


def test_training_export_excludes_drafts_evaluation_and_heldout_intents():
    workflow=script('review_workflow')
    row=SimpleNamespace(status='proposed',purpose='runtime',license='CC0-1.0',source_language='hindi',
        target_language='bengali',source_text='नया पाठ',proposed_target='নতুন পাঠ')
    assert not workflow.eligible_training(row,set())
    row.status='reviewed';row.purpose='evaluation'
    assert not workflow.eligible_training(row,set())
    row.purpose='runtime'
    assert workflow.eligible_training(row,set())
    from app.services.translation.corpus import normalize_source
    assert not workflow.eligible_training(row,{('hindi',normalize_source(row.source_text))})


def test_additive_migration_is_idempotent_and_preserves_existing_rows(tmp_path):
    engine=create_engine('sqlite:///'+(tmp_path/'old.db').as_posix())
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(100), created_at DATETIME)'))
        conn.execute(text("INSERT INTO users(id,username) VALUES(42,'existing')"))
    migrate(engine);migrate(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT username FROM users WHERE id=42')).scalar()=='existing'
        assert conn.execute(text('SELECT count(*) FROM schema_versions')).scalar()==1
        assert conn.execute(text('SELECT count(*) FROM correction_reports')).scalar()==0
    engine.dispose()


def test_backup_restore_retains_committed_data_and_refuses_overwrite(tmp_path):
    ops=script('database_ops')
    source=tmp_path/'live.db';backup=tmp_path/'backup.db';restore=tmp_path/'restored.db'
    connection=sqlite3.connect(source)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('CREATE TABLE sample (value TEXT)')
    connection.execute("INSERT INTO sample VALUES ('committed')");connection.commit()
    assert ops.copy_database(source,backup)['integrity']=='ok'
    assert ops.copy_database(backup,restore)['table_counts']=={'sample':1}
    with pytest.raises(ValueError):ops.copy_database(backup,source)
    connection.close()


def test_request_deadline_keeps_capacity_reserved_until_native_work_exits(db_session, monkeypatch):
    monkeypatch.setattr(settings,'REQUEST_TIMEOUT_SECONDS',.03)
    slots=threading.BoundedSemaphore(1);monkeypatch.setattr(runtime,'_slots',slots)
    released=threading.Event()
    async def exercise():
        def slow(db):
            try: time.sleep(.12);return SimpleNamespace(context_status='local_only')
            finally: released.set()
        with pytest.raises(HTTPException) as timeout:
            await runtime.run_inference(slow,db_session,1,'deadline_test','hindi','marathi')
        assert timeout.value.status_code==504
        with pytest.raises(HTTPException) as busy:
            await runtime.run_inference(slow,db_session,1,'deadline_test','hindi','marathi')
        assert busy.value.status_code==503
        await asyncio.to_thread(released.wait,1)
        await asyncio.sleep(.02)
    asyncio.run(exercise())
    assert slots.acquire(blocking=False);slots.release()


def test_metrics_do_not_include_source_text(client, monkeypatch):
    from app.api.routes import analyze
    from app.schemas.analyze import AnalyzeResponse
    secret_phrase='PRIVATE_SENTENCE_FOR_METRICS_TEST'
    monkeypatch.setattr(analyze,'analyze_sync',lambda request,db: AnalyzeResponse(
        detected_language='hindi',detected_script='latin',normalized_text=request.text,native_text='पाठ',roman_text='paath',
        translation='पाठ',translation_native='पाठ',translation_roman='paath',english_meaning='Text.'))
    assert client.post('/api/analyze',json={'text':secret_phrase,'source_language':'hindi','target_language':'marathi'}).status_code==200
    result=client.get('/api/operations/metrics')
    assert result.status_code==200 and secret_phrase not in result.text


def test_explanation_error_does_not_fall_back_to_an_ungrounded_legacy_match(monkeypatch):
    from app.services.explanation.engine import HybridExplanationEngine
    engine=HybridExplanationEngine()
    def broken(**kwargs):raise ValueError('private sentence must not be logged')
    monkeypatch.setattr(engine,'_explain_enhanced',broken)
    result=engine.explain('मुझे पानी चाहिए','hindi','मला पाणी पाहिजे','marathi',use_tutor=False)
    assert result['explanation_source']=='unavailable' and result['grammar_points']==[]


def test_production_rejects_local_identity_and_insecure_cookies():
    with pytest.raises(ValueError):Settings(_env_file=None,APP_ENV='production',AUTH_MODE='local',COOKIE_SECURE=False)


def test_account_export_and_deletion_do_not_expose_credentials(client,db_session):
    body={'username':'export_user','password':'A private test password!'}
    response=client.post('/api/auth/register',json=body)
    assert response.status_code==201
    user_id=response.json()['id'];client.headers['X-CSRF-Token']=client.cookies['bb_csrf']
    exported=client.get('/api/auth/export')
    assert exported.status_code==200
    assert 'password_hash' not in exported.text and 'token_hash' not in exported.text
    assert client.request('DELETE','/api/auth/account',json={'password':body['password']}).status_code==200
    db_session.expire_all()
    assert db_session.get(AccountCredential,user_id) is None
    assert db_session.query(AuthSession).filter_by(user_id=user_id).count()==0
    assert db_session.get(User,user_id).username.startswith('deleted_')


def test_maintenance_preserves_current_and_persistent_cloud_budgets(db_session):
    from datetime import timedelta
    from app.services.activity import now_utc
    from app.models.entities import UsageCounter
    now=now_utc()
    db_session.add_all([UsageCounter(key='expired',count=3,expires_at=now-timedelta(days=1)),
        UsageCounter(key='cloud:run:frozen',count=6,expires_at=now+timedelta(days=3650))])
    db_session.commit()
    maintenance=script('maintenance')
    assert maintenance.prune(db_session)['expired_quota_windows']==1
    assert db_session.get(UsageCounter,'expired') is not None
    assert maintenance.prune(db_session,True)['expired_quota_windows']==1
    assert db_session.get(UsageCounter,'cloud:run:frozen').count==6


def test_deployment_check_requires_migrated_schema_and_account_configuration(db_session):
    checker=script('deployment_check')
    assert not checker.check(settings,db_session.get_bind())['configuration_ready']
    production=settings.model_copy(update={'APP_ENV':'production','AUTH_MODE':'accounts','COOKIE_SECURE':True,
        'TESTING':False,'USE_MOCK_MODELS':False,'ALLOW_SQLITE_FALLBACK':False,'CORS_ORIGINS':['https://example.org']})
    migrate(db_session.get_bind())
    assert checker.check(production,db_session.get_bind())['configuration_ready']
