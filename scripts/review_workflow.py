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
    return {(r['source_language'],normalize_source(r[key])) for r in rows for key in ('native_source','roman_source')}


def eligible_training(row, forbidden):
    from app.services.translation.corpus import normalize_source
    return (row.status=='reviewed' and row.purpose=='runtime'
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
    args=parser.parse_args()
    from app.models.database import SessionLocal,init_db
    from app.models.entities import User,AccountCredential,CorrectionReport,CorrectionEvent,ReviewedTranslation
    from app.api.routes.corrections import dto
    from app.services.translation.corpus import normalize_source
    from sqlalchemy.exc import IntegrityError
    init_db()
    with SessionLocal() as db:
        if args.command=='set-reviewer':
            user=db.query(User).filter_by(username=args.username.lower()).first()
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
            row=db.get(CorrectionReport,args.report_id)
            if row is None or not eligible_training(row,forbidden):
                raise ValueError('Requires reviewed, licensed, non-evaluation content outside frozen source/target intents')
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
            decision=db.query(CorrectionEvent).filter_by(report_id=row.id,action='reviewed').order_by(CorrectionEvent.id.desc()).first()
            if not decision: continue
            output.append({**dto(row),'reviewer_id':decision.actor_id,'review_date':decision.created_at.isoformat(),
                           'audit_event_id':decision.id})
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'purpose':args.command,'rows':output,'count':len(output)},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'exported':len(output),'purpose':args.command}))


if __name__=='__main__': main()
