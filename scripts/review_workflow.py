"""Operator tools for review roles, draft imports and gated exports. Never auto-review."""
import argparse
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def frozen_sources():
    from runtime_evaluation import load_cases
    from app.services.translation.corpus import normalize_source
    _,rows=load_cases()
    forbidden = {(r['source_language'],normalize_source(r[key])) for r in rows for key in ('native_source','roman_source')}
    base = ROOT / "data" / "processed"
    files = [base / "translation" / "test.jsonl", base / "expanded" / "translation" / "test.jsonl"]
    files.extend(sorted((base / "translation-quality-v1").glob("*.jsonl")))
    files.extend(sorted((base / "translation-quality-v2").glob("*.jsonl")))
    for path in files:
        if path.name == "train.jsonl":
            continue
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                row = json.loads(line)
                if "sentences" in row:
                    values = row["sentences"].items()
                elif "source_language" in row:
                    values = ((row["source_language"], row["source_text"]),
                              (row["target_language"], row["target_text"]))
                else:
                    values = ((language, row[language]) for language in ("hindi", "marathi"))
                forbidden.update((language, normalize_source(text)) for language, text in values if text)
    return forbidden


def eligible_training(row, forbidden):
    from app.services.translation.corpus import normalize_source
    return (row.status=='reviewed' and row.purpose=='runtime'
            and row.publication_consent and bool((row.proposed_target or "").strip())
            and row.license in ('CC0-1.0','CC-BY-4.0')
            and (row.source_language,normalize_source(row.source_text)) not in forbidden
            and (row.target_language,normalize_source(row.proposed_target or '')) not in forbidden)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    role=sub.add_parser('set-reviewer');role.add_argument('--username',required=True)
    draft=sub.add_parser('import-drafts');draft.add_argument('--owner-id',type=int,default=1)
    export=sub.add_parser('export-training');export.add_argument('--output',type=Path,required=True)
    evaluation=sub.add_parser('export-evaluation');evaluation.add_argument('--output',type=Path,required=True)
    publish=sub.add_parser('publish-memory');publish.add_argument('--report-id',required=True)
    publish.add_argument('--version',type=int,required=True)
    args=parser.parse_args()
    from app.models.database import SessionLocal
    from app.core.auth import lock_account
    from app.models.entities import User,AccountCredential,CorrectionReport,CorrectionEvent,ReviewedTranslation
    from app.api.routes.corrections import dto
    from app.services.translation.corpus import normalize_source
    with SessionLocal() as db:
        if args.command=='set-reviewer':
            user=db.query(User).filter_by(username=args.username.lower()).first()
            if user:
                lock_account(db, user.id)
            credential=db.get(AccountCredential,user.id) if user else None
            if not credential: raise ValueError('Create a named account first; the demo user cannot be a reviewer')
            credential.role='reviewer';db.commit();print('Reviewer role assigned to the named account.');return
        if args.command=='import-drafts':
            from runtime_evaluation import load_cases
            _,rows=load_cases()
            if not db.get(User,args.owner_id): raise ValueError('Unknown owner')
            existing={row[0] for row in db.query(CorrectionReport.evaluation_id).all()}
            count=0
            for case in rows:
                if case['id'] in existing: continue
                row=CorrectionReport(id=str(uuid.uuid4()),user_id=args.owner_id,evaluation_id=case['id'],
                    source_language=case['source_language'],target_language=case['target_language'],source_text=case['native_source'],
                    observed_target=case['draft_target'],proposed_target=case['draft_target'],proposed_roman=case['draft_roman'],
                    proposed_english=case['draft_english_intent'],category='other',purpose='evaluation',status='proposed',
                    note='AI-authored draft; verify native/Roman source, target, intent and ambiguity before any human review decision.',
                    provenance=case['provenance'],license=case['license'])
                db.add(row);db.flush()
                db.add(CorrectionEvent(report_id=row.id,actor_id=args.owner_id,action='draft_import',snapshot_json=json.dumps(dto(row),ensure_ascii=False)))
                count+=1
            db.commit();print(json.dumps({'drafts_imported':count,'human_reviews_created':0}));return
        forbidden=frozen_sources()
        if args.command=='publish-memory':
            from sqlalchemy import text
            if db.get_bind().dialect.name == "sqlite":
                db.execute(text("BEGIN IMMEDIATE"))
            row=db.get(CorrectionReport,args.report_id,with_for_update=True)
            if row is None or row.version != args.version or not eligible_training(row,forbidden):
                raise ValueError('Requires the current reviewed version, consent, license and content outside held-out data')
            if not review_event(db, row, CorrectionEvent):
                raise ValueError('The version must have a human review event')
            key=normalize_source(row.source_text)
            current=db.query(ReviewedTranslation).filter_by(source_language=row.source_language,target_language=row.target_language,source_key=key).first()
            if current:
                raise ValueError('An existing memory entry needs explicit conflict resolution; it will not be overwritten')
            db.add(ReviewedTranslation(source_language=row.source_language,target_language=row.target_language,
                source_key=key,source_text=row.source_text,target_text=row.proposed_target,target_roman=row.proposed_roman,
                english_meaning=row.proposed_english,provenance='review_queue:'+row.id))
            db.commit();print('Published the reviewed correction to exact memory.');return
        if args.output.exists(): raise ValueError('Choose a new output; exports never overwrite prior artifacts')
        rows=db.query(CorrectionReport).filter_by(status='reviewed').all()
        if args.command=='export-training': rows=[row for row in rows if eligible_training(row,forbidden)]
        else: rows=[row for row in rows if row.purpose=='evaluation' and row.evaluation_id]
        output=[]
        for row in rows:
            decision=review_event(db, row, CorrectionEvent)
            if not decision: continue
            output.append({**dto(row),'reviewer_id':decision.actor_id,'review_date':decision.created_at.isoformat(),
                           'audit_event_id':decision.id})
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x", encoding="utf-8") as destination:
            json.dump({'purpose':args.command,'rows':output,'count':len(output)}, destination, ensure_ascii=False, indent=2)
        print(json.dumps({'exported':len(output),'purpose':args.command}))


def review_event(db, row, event_model):
    decision = db.query(event_model).filter_by(report_id=row.id, action='reviewed').order_by(event_model.id.desc()).first()
    return decision if decision and json.loads(decision.snapshot_json).get("version") == row.version else None


if __name__=='__main__': main()
