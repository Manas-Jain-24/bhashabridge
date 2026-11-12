"""Explicitly triggered, bounded provider smoke; never an accuracy benchmark."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--max-calls',type=int,default=3);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if not 1<=args.max_calls<=6: p.error('Smoke budget must be between 1 and 6 calls')
    if args.output.exists(): raise ValueError('Choose a new report; do not overwrite smoke evidence')
    from runtime_evaluation import load_cases
    from app.services.translation.contextual import ContextualTranslator
    from app.services.explanation.llm_tutor import llm_tutor
    from app.services.runtime import budget
    from app.core.config import settings
    _,cases=load_cases()
    if not llm_tutor.is_available: raise RuntimeError('A configured, non-mock Gemini credential is required')
    remaining=args.max_calls
    def reserve():
        nonlocal remaining
        if remaining<=0:return False
        remaining-=1;return True
    token=budget.set(reserve)
    results=[]
    try:
        for case in cases[:args.max_calls]:
            started=time.monotonic()
            # Fresh circuit for each direction; no retries or secondary tutor calls.
            candidate,status=ContextualTranslator().refine(case['roman_source'],case['native_source'],case['source_language'],case['target_language'])
            results.append({'id':case['id'],'source_language':case['source_language'],'target_language':case['target_language'],
                'status':status,'seconds':round(time.monotonic()-started,3),
                'response':candidate.model_dump() if candidate else None})
            if remaining and case is not cases[args.max_calls-1]:time.sleep(5)
    finally: budget.reset(token)
    report={'scope':'Provider-only smoke; no local neural inference or human scoring', 'human_reviewed':False,
        'model':settings.GEMINI_TRANSLATION_MODEL,'call_budget':args.max_calls,'calls_reserved':args.max_calls-remaining,
        'max_output_tokens_per_call':settings.GEMINI_MAX_OUTPUT_TOKENS,'attempts':results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='attempts'},indent=2))
    print(json.dumps({'statuses':[r['status'] for r in results]}))
    raise SystemExit(0 if all(r['status']=='assisted' for r in results) else 1)


if __name__=='__main__':main()
