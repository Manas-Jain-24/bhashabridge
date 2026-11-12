"""Compare structural diagnostics without treating draft references as accuracy."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def summarize(path):
    from app.services.translation.contextual import protected_values
    report=json.loads(path.read_text(encoding='utf-8'))
    slices=defaultdict(list)
    for row in report['attempts']:
        slices[row['source_language']+'->'+row['target_language']].append(row)
    summaries={}
    for direction,rows in slices.items():
        supported=Counter();errors=Counter();categories=Counter()
        for row in rows:
            result=row.get('result')
            if result is None:
                errors[str(row.get('http_status') or row.get('error'))]+=1
                categories[row['category']]+=1
                continue
            expected=protected_values(row['request']['text'])
            for view in ('native_text','translation_native','translation_roman','english_meaning'):
                if not result.get(view):supported[view+':unavailable']+=1
                elif protected_values(result[view])!=expected:supported[view+':protected_value_failure']+=1
            if result.get('explanation_source')=='unavailable':supported['explanation:unavailable']+=1
        summaries[direction]={'requests':len(rows),'responses':sum('result' in r for r in rows),
            'errors_by_status':dict(errors),'error_categories':dict(categories),'supporting_view_checks':dict(supported),
            'model_sources':dict(Counter(r.get('result',{}).get('model_source','error') for r in rows)),
            'context_status':dict(Counter(r.get('result',{}).get('context_status','error') for r in rows))}
    return {'report':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'complete':report['complete'],'expected_requests':report['expected_requests'],
        'directions':summaries,'latency':report['summary']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Choose a new output; evidence is never overwritten')
    result={'human_reviewed':False,'accuracy_score':None,'model_promotion':False,
        'interpretation':'Observed structural regression results, not held-out semantic quality.',
        'reports':[summarize(path) for path in args.reports]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'reports':len(result['reports']),'complete':all(r['complete'] for r in result['reports'])}))
