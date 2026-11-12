"""Bounded inference, end-to-end deadlines and text-free runtime measurements."""
import asyncio
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from datetime import datetime, timezone
import threading
import time

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings

deadline = ContextVar('inference_deadline', default=None)
budget = ContextVar('cloud_budget', default=None)
stages = ContextVar('inference_stages', default=None)
_executor = ThreadPoolExecutor(max_workers=settings.INFERENCE_WORKERS, thread_name_prefix='inference')
_slots = threading.BoundedSemaphore(settings.INFERENCE_WORKERS)
_lock = threading.Lock()
_samples = deque(maxlen=2000)
_counts = Counter()
_provider = {'last_success_utc':None, 'last_failure_utc':None, 'last_failure_kind':None}


def check_deadline():
    until = deadline.get()
    if until is not None and time.monotonic() >= until:
        raise HTTPException(504, 'Translation exceeded the request time budget. Please retry.')


@contextmanager
def stage(name):
    check_deadline()
    started = time.monotonic()
    try:
        yield
    finally:
        values = stages.get()
        if values is not None:
            values[name] = round((time.monotonic()-started)*1000, 2)


def cloud_allowed():
    check_deadline()
    callback = budget.get()
    if callback:
        return callback()
    if settings.TESTING or settings.USE_MOCK_MODELS:
        return True
    from app.models.database import SessionLocal
    from app.services.limits import reserve_cloud
    with SessionLocal() as db:
        return reserve_cloud(db, settings.LOCAL_USER_ID)


def provider_event(success, kind=None):
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        if success:
            _provider['last_success_utc'] = now
        else:
            _provider.update(last_failure_utc=now, last_failure_kind=kind)


def provider_status():
    with _lock:
        return dict(_provider)


def metrics():
    with _lock:
        samples, counts = list(_samples), dict(_counts)
    groups = {}
    for row in samples:
        key = '|'.join((row['route'], row['source'], row['target'], row['temperature']))
        groups.setdefault(key, []).append(row)
    result = {}
    def summary(values):
        ordered = sorted(values)
        return {f'p{p}_ms':ordered[min(len(ordered)-1, int((len(ordered)-1)*p/100))] for p in (50,95,99)}
    for key, rows in groups.items():
        result[key] = {'samples':len(rows), **summary([r['elapsed_ms'] for r in rows]),
                       'stages':{name:summary([r['stages'][name] for r in rows if name in r['stages']])
                                 for name in {name for r in rows for name in r['stages']}}}
    return {'scope':'this process; last 2000 requests', 'counts':counts, 'latency':result,
            'provider':provider_status()}


async def run_inference(operation, db, user_id, route, source, target):
    if not _slots.acquire(blocking=False):
        with _lock:
            _counts[f'{route}:busy'] += 1
        raise HTTPException(503, 'Inference is busy. Retry shortly.', headers={'Retry-After':'2'})
    from app.services.translation.indictrans2 import indictrans2_adapter
    from app.services.limits import reserve_cloud
    started = time.monotonic()
    cold = not indictrans2_adapter.is_loaded
    timeout = settings.REQUEST_TIMEOUT_SECONDS
    bind = db.get_bind()
    # Each worker owns its session; a timed-out request cannot close its database.
    def execute():
        stage_values = {}
        deadline_token = deadline.set(started+timeout)
        stage_token = stages.set(stage_values)
        outcome, context, issue = 'error', None, None
        with Session(bind=bind) as worker_db:
            budget_token = budget.set(lambda: reserve_cloud(worker_db, user_id))
            try:
                check_deadline()
                result = operation(worker_db)
                check_deadline()
                outcome = 'ok'
                context = getattr(result, 'context_status', None)
                issue = getattr(result, 'context_issue', None)
                return result
            finally:
                budget.reset(budget_token); deadline.reset(deadline_token); stages.reset(stage_token)
                row = {'route':route, 'source':source, 'target':target,
                       'temperature':'cold' if cold else 'warm', 'elapsed_ms':round((time.monotonic()-started)*1000,2),
                       'stages':stage_values}
                with _lock:
                    _samples.append(row); _counts[f'{route}:{outcome}'] += 1
                    if context:
                        _counts[f'context:{context}'] += 1
                    if issue in ('unavailable','cooldown','busy','budget_exhausted','rejected','provider_error'):
                        _counts[f'context_issue:{issue}'] += 1
    try:
        future = _executor.submit(copy_context().run, execute)
    except Exception:
        _slots.release()
        raise
    future.add_done_callback(lambda _: _slots.release())
    wrapped = asyncio.wrap_future(future)
    wrapped.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)
    try:
        return await asyncio.wait_for(asyncio.shield(wrapped), timeout)
    except asyncio.TimeoutError:
        with _lock:
            _counts[f'{route}:timeout'] += 1
        # Native inference cannot safely be killed in a thread. Its capacity stays
        # occupied until it exits, and later stages cannot start after the deadline.
        raise HTTPException(504, 'Translation exceeded the request time budget. Please retry.')
