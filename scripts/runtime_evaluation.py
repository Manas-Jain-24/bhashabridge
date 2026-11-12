"""Resumable full-runtime draft diagnostics. No automatic human-quality scores."""
import argparse
import asyncio
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
DATA=ROOT/'data/quality/evaluation-draft-v1'


def load_cases(directory=DATA):
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    for name,key in [('cases.jsonl','cases_sha256'),('intents.tsv','catalog_sha256')]:
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=manifest[key]:
            raise ValueError(f'Frozen evaluation changed: {name}')
    rows=[json.loads(line) for line in (directory/'cases.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(rows)!=300 or len({r['id'] for r in rows})!=300:
        raise ValueError('Missing or duplicate evaluation cases')
    directions=Counter((r['source_language'],r['target_language']) for r in rows)
    if len(directions)!=6 or set(directions.values())!={50}:
        raise ValueError('Each of six directions requires 50 intents')
    groups=defaultdict(set)
    for row in rows:
        groups[row['group_id']].add(row['split'])
        if row['review_status']!='draft' or row['reviewer'] or row['acceptable_references']:
            raise ValueError('This frozen version is explicitly unreviewed; put review decisions in a separate artifact')
    if any(len(splits)!=1 for splits in groups.values()):
        raise ValueError('Semantic family leaks across splits')
    return manifest,rows


def edit_distance(left,right):
    previous=list(range(len(right)+1))
    for i,a in enumerate(left,1):
        current=[i]
        for j,b in enumerate(right,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(a!=b)))
        previous=current
    return previous[-1]


def summarize(attempts):
    slices=defaultdict(list)
    for row in attempts:
        slices[f"{row['source_language']}->{row['target_language']}:{row['path']}"] .append(row)
    summary={}
    for key,rows in slices.items():
        values=sorted(row['elapsed_seconds'] for row in rows)
        summary[key]={'attempted':len(rows),'responses':sum('result' in r for r in rows),
            'errors':dict(Counter(r['error'] for r in rows if 'error' in r)),
            'assisted':sum(r.get('result',{}).get('context_status')=='assisted' for r in rows),
            'fallbacks':sum(r.get('result',{}).get('context_status')=='unavailable' for r in rows),
            'memory_hits':sum(r.get('result',{}).get('context_status')=='reviewed' for r in rows),
            'protected_value_failures':sum(r.get('protected_values_preserved') is False for r in rows),
            'p50_seconds':values[(len(values)-1)//2], 'p95_seconds':values[int((len(values)-1)*.95)],
            'draft_reference_exact_matches':sum(r.get('draft_reference_exact') is True for r in rows),
            'warning':'Draft comparisons and source-estimate CER are diagnostics, not reviewed accuracy.'}
    return summary


def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)


async def run(args):
    from app.core.config import settings
    from app.models.database import init_db
    from app.api.routes.analyze import analyze_sync
    from app.schemas.analyze import AnalyzeRequest
    from app.services.runtime import run_inference, metrics
    from app.services.translation.contextual import protected_values, PROMPT_VERSION
    from app.services.translation.indictrans2 import indictrans2_adapter
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    try:
        import torch
        torch.set_num_threads(2)
    except ImportError:
        pass
    manifest,rows=load_cases(args.cases)
    if args.split!='all': rows=[r for r in rows if r['split']==args.split]
    if args.limit: rows=rows[:args.limit]
    paths=['native_local','roman_local'] if args.mode=='local' else ['roman_hybrid']
    if args.mode=='hybrid' and args.max_cloud_calls<=0:
        raise ValueError('Hybrid requires an explicit positive --max-cloud-calls budget')
    settings.CLOUD_CALLS_PER_DAY=args.max_cloud_calls
    settings.CLOUD_USER_CALLS_PER_DAY=args.max_cloud_calls
    settings.CLOUD_TOTAL_CALLS=args.max_cloud_calls
    settings.CLOUD_TOTAL_SCOPE=hashlib.sha256(str(args.output.resolve()).encode()).hexdigest()
    protocol={'cases_sha256':manifest['cases_sha256'],'mode':args.mode,'split':args.split,
              'limit':args.limit,'max_cloud_calls':args.max_cloud_calls,
              'model':settings.INDICTRANS2_MODEL_CHECKPOINT,'gemini_model':settings.GEMINI_TRANSLATION_MODEL,
              'prompt_version':PROMPT_VERSION,'timeout_seconds':settings.REQUEST_TIMEOUT_SECONDS,
              'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'translation_engine':settings.TRANSLATION_ENGINE,'mock_models':settings.USE_MOCK_MODELS,
              'bengali_neural_transliteration':settings.BENGALI_NEURAL_TRANSLITERATION,
              'backend_sha256':hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'backend/app').rglob('*.py')))).hexdigest()}
    if args.output.exists():
        if not args.resume: raise ValueError('Use a new output path or --resume; reports are never silently overwritten')
        report=json.loads(args.output.read_text(encoding='utf-8'))
        if report['protocol']!=protocol: raise ValueError('Resume protocol/code/data mismatch; start a new report')
    else:
        report={'protocol':protocol,'human_reviewed':False,'accuracy_score':None,'promotion_eligible':False,
                'scope':'Frozen draft diagnostics; no human quality scoring','complete':False,
                'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
                'expected_requests':len(rows)*len(paths),'attempts':[]}
    done={(row['id'],row['path']) for row in report['attempts']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    # Persistent isolated DB beside a resumable report retains its cloud budget.
    db_path=args.output.with_suffix('.sqlite3').resolve()
    engine=create_engine('sqlite:///'+db_path.as_posix(),connect_args={'check_same_thread':False})
    init_db(engine,seed=True)
    try:
        for row in rows:
            for path in paths:
                if (row['id'],path) in done: continue
                source=row['native_source'] if path=='native_local' else row['roman_source']
                request=AnalyzeRequest(text=source,source_language=row['source_language'],target_language=row['target_language'],
                                       translation_mode='hybrid' if path=='roman_hybrid' else 'local')
                attempt={key:row[key] for key in ('id','intent_id','group_id','split','source_language','target_language','category')}
                attempt.update(path=path,request=request.model_dump())
                started=time.monotonic()
                try:
                    with Session(engine) as db:
                        value=await run_inference(lambda session: analyze_sync(request,session),db,1,'evaluation',row['source_language'],row['target_language'])
                    result=value.model_dump()
                    attempt.update(result=result,protected_values_preserved=protected_values(source)==protected_values(result['translation_native']),
                        source_estimate_cer_against_draft=edit_distance(result['native_text'],row['native_source'])/max(1,len(row['native_source'])),
                        draft_reference_exact=result['translation_native'].strip()==row['draft_target'].strip())
                except Exception as error:
                    attempt.update(error=type(error).__name__,http_status=getattr(error,'status_code',None))
                attempt['elapsed_seconds']=round(time.monotonic()-started,3)
                report['attempts'].append(attempt)
                report['summary']=summarize(report['attempts'])
                save(args.output,report)
                print(f"{len(report['attempts'])}/{report['expected_requests']} {row['id']} {path}",flush=True)
                if args.pause: await asyncio.sleep(args.pause)
        report.update(complete=len(report['attempts'])==report['expected_requests'],runtime_metrics=metrics(),
            model_revision=getattr(getattr(indictrans2_adapter.model,'config',None),'_commit_hash',None))
        if indictrans2_adapter.model is not None:
            parameter=next(indictrans2_adapter.model.parameters())
            report['hardware']={'device':str(parameter.device),'dtype':str(parameter.dtype),
                'torch':torch.__version__,'device_name':torch.cuda.get_device_name() if parameter.is_cuda else 'CPU'}
        save(args.output,report)
    finally:
        engine.dispose()
    print(json.dumps({'complete':report['complete'],'requests':len(report['attempts']),'summary':report['summary']},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=Path,default=DATA)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mode',choices=['local','hybrid'],default='local')
    parser.add_argument('--split',choices=['all','development','test'],default='all')
    parser.add_argument('--limit',type=int,default=0)
    parser.add_argument('--max-cloud-calls',type=int,default=0)
    parser.add_argument('--pause',type=float,default=0)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if args.limit<0 or not 0<=args.max_cloud_calls<=100 or not 0<=args.pause<=60:
        parser.error('Invalid limit, cloud budget (0–100), or pause (0–60)')
    asyncio.run(run(args))


if __name__=='__main__': main()
