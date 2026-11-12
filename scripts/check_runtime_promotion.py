"""A fail-closed promotion decision: structural scores never substitute for people."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


def evaluate(baseline, candidate, reviews=None, max_p95=60):
    reasons=[]
    if not baseline.get('complete') or not candidate.get('complete'): reasons.append('incomplete_run')
    if baseline.get('protocol',{}).get('cases_sha256')!=candidate.get('protocol',{}).get('cases_sha256'):
        reasons.append('different_evaluation_data')
    base={(r['id'],r['path']):r for r in baseline.get('attempts',[])}
    cand={(r['id'],r['path']):r for r in candidate.get('attempts',[])}
    for report,unique in ((baseline,base),(candidate,cand)):
        if len(unique)!=len(report.get('attempts',[])) or report.get('expected_requests')!=len(unique):
            reasons.append('invalid_attempt_count')
    if not baseline.get('protocol',{}).get('cases_sha256'):
        reasons.append('missing_dataset_hash')
    if set(base)!=set(cand) or not base: reasons.append('different_or_empty_request_matrix')
    if not reviews or not reviews.get('human_reviewed'):
        reasons.append('independent_human_review_required')
    annotations={(r['id'],r['path']):r for r in (reviews or {}).get('reviews',[])}
    slices=defaultdict(lambda:{'n':0,'baseline_adequate':0,'candidate_adequate':0})
    for key,row in cand.items():
        if row.get('split')!='test': reasons.append('promotion_requires_heldout_test_split')
        if 'error' in row or row.get('protected_values_preserved') is False:
            reasons.append('candidate_structural_failure')
        review=annotations.get(key)
        required=('baseline_adequate','candidate_adequate','baseline_critical','candidate_critical')
        if (not review or not review.get('reviewer') or not review.get('reviewed_at')
                or any(type(review.get(field)) is not bool for field in required)):
            reasons.append('missing_review_annotations');continue
        if review['candidate_critical'] and not review['baseline_critical']:
            reasons.append('new_critical_meaning_error')
        name=row['source_language']+'->'+row['target_language']+':'+row['path']
        value=slices[name];value['n']+=1
        value['baseline_adequate']+=int(review['baseline_adequate'])
        value['candidate_adequate']+=int(review['candidate_adequate'])
    if slices and any(v['candidate_adequate']<v['baseline_adequate'] for v in slices.values()):
        reasons.append('per_direction_regression')
    if slices and any(v['n']<20 for v in slices.values()):
        reasons.append('insufficient_reviewed_coverage')
    if not slices or sum(v['candidate_adequate'] for v in slices.values())<=sum(v['baseline_adequate'] for v in slices.values()):
        reasons.append('no_reviewed_adequacy_improvement')
    if not candidate.get('summary') or not math.isfinite(max_p95) or max_p95<=0:
        reasons.append('invalid_latency_evidence_or_budget')
    if any(not isinstance(v.get('p95_seconds'),(int,float)) or not math.isfinite(v['p95_seconds'])
           or v['p95_seconds']>max_p95 for v in candidate.get('summary',{}).values()):
        reasons.append('latency_budget_exceeded')
    return {'promote':not reasons,'reasons':sorted(set(reasons)),'reviewed_slices':dict(slices),
            'note':'This decision does not activate a model. Preserve the current model until all gates pass.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--reviews',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-p95',type=float,default=60)
    args=p.parse_args()
    if args.output.exists(): raise ValueError('Use a new decision output path')
    baseline=json.loads(args.baseline.read_text(encoding='utf-8'));candidate=json.loads(args.candidate.read_text(encoding='utf-8'))
    reviews=json.loads(args.reviews.read_text(encoding='utf-8')) if args.reviews else None
    if reviews:
        for key,path in [('baseline_sha256',args.baseline),('candidate_sha256',args.candidate)]:
            if reviews.get(key)!=hashlib.sha256(path.read_bytes()).hexdigest(): raise ValueError('Review artifact is not bound to these exact reports')
    result=evaluate(baseline,candidate,reviews,args.max_p95)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['promote'] else 1)


if __name__=='__main__':main()
