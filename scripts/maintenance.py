"""Prune expired sessions, rate windows and practice issues; keep learning history."""
import argparse
from datetime import timedelta
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def prune(db, apply=False):
    from app.models.entities import AuthSession,UsageCounter,PracticeIssue
    from app.services.activity import now_utc
    now=now_utc()
    queries={'expired_sessions':db.query(AuthSession).filter(AuthSession.expires_at<now),
             'expired_quota_windows':db.query(UsageCounter).filter(UsageCounter.expires_at<now),
             'expired_practice_issues':db.query(PracticeIssue).filter(PracticeIssue.issued_at<now-timedelta(days=1))}
    counts={name:query.count() for name,query in queries.items()}
    if apply:
        for query in queries.values():query.delete(synchronize_session=False)
        db.commit()
    return {'applied':apply,**counts}


if __name__=='__main__':
    import json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Without this flag, print counts only')
    args=parser.parse_args()
    from app.models.database import SessionLocal
    with SessionLocal() as db:print(json.dumps(prune(db,args.apply),indent=2))
