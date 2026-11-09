"""Train, select on validation, then evaluate once on the frozen fresh test."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
EXPERIMENT=ROOT/'ml/experiments/translation-lora-v1'
EVALUATION=ROOT/'ml/evaluation/quality-v1'


def run(*args):
    subprocess.run([sys.executable,'-u',*map(str,args)],cwd=ROOT,check=True)


def score(directory,source='bengali',target='marathi'):
    path=directory/f'{source}-{target}.json'
    value=json.loads(path.read_text(encoding='utf-8'))
    if not value['complete']: raise ValueError('Incomplete evaluation')
    return {key:value[key] for key in ('bleu','chrf_plus_plus','inference_failures')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-training',action='store_true')
    args=parser.parse_args()
    if not args.skip_training: run('scripts/train_translation_adapter.py')
    training=json.loads((EXPERIMENT/'training_report.json').read_text())
    if not training['complete']: raise ValueError('Training incomplete')
    EVALUATION.mkdir(parents=True,exist_ok=True)
    evaluate='scripts/evaluate_translation_quality.py'
    # The previous pipeline is compared on validation only. Test is not inspected.
    run(evaluate,'--split','validation','--legacy-processor','--output',EVALUATION/'validation-legacy')
    run(evaluate,'--split','validation','--output',EVALUATION/'validation-baseline')
    baseline=score(EVALUATION/'validation-baseline')
    candidates=[]
    for epoch in (1,2):
        directory=EVALUATION/f'validation-epoch-{epoch}'
        run(evaluate,'--split','validation','--pair-only','--adapter',EXPERIMENT/f'epoch-{epoch}','--output',directory)
        candidates.append({'epoch':epoch,**score(directory)})
    best=max(candidates,key=lambda r:(r['chrf_plus_plus'],r['bleu'],-r['inference_failures'],-r['epoch']))
    checkpoint=EXPERIMENT/f'epoch-{best["epoch"]}'
    eligible=(best['chrf_plus_plus']>=baseline['chrf_plus_plus']+0.5 and best['bleu']>=baseline['bleu']
              and best['inference_failures']<=baseline['inference_failures'])
    selection={'selection_used':'validation_only','scope':['bengali','marathi'],
               'baseline':baseline,'candidates':candidates,'selected_epoch':best['epoch'],
               'adapter':checkpoint.relative_to(ROOT).as_posix(),
               'adapter_sha256':hashlib.sha256((checkpoint/'adapter_model.safetensors').read_bytes()).hexdigest(),
               'validation_gate_passed':eligible,
               'validation_gate':{'minimum_chrf_gain':0.5,'minimum_bleu_gain':0,'additional_failures_allowed':0},
               'test_gate':{'minimum_chrf_gain':0,'maximum_bleu_loss':0.5,'additional_failures_allowed':0},
               'test_used_for_epoch_selection':False}
    selection_path=EXPERIMENT/'selection.json'
    if selection_path.exists() and json.loads(selection_path.read_text())!=selection:
        raise ValueError('Frozen selection changed; do not tune on the test')
    selection_path.write_text(json.dumps(selection,indent=2),encoding='utf-8')
    print('Validation selection frozen:',json.dumps(selection),flush=True)
    # Test both the fixed baseline (all directions) and the selected experimental
    # pair. A rejected candidate stays a research result, not a deployed model.
    run(evaluate,'--split','test','--output',EVALUATION/'test-baseline')
    run(evaluate,'--split','test','--pair-only','--adapter',checkpoint,'--output',EVALUATION/'test-candidate')
    test_base=score(EVALUATION/'test-baseline'); test_candidate=score(EVALUATION/'test-candidate')
    accepted=(eligible and test_candidate['chrf_plus_plus']>test_base['chrf_plus_plus']
              and test_candidate['bleu']>=test_base['bleu']-0.5
              and test_candidate['inference_failures']<=test_base['inference_failures'])
    result={'complete':True,'selection':selection,'test_baseline':test_base,'test_candidate':test_candidate,
            'promotion_recommended':accepted,'production_scope':['bengali','marathi'],
            'limitations':['Fresh document-separated NTREX news subset; not general accuracy.',
                           'Upstream pretrained exposure unknown.','Correction drafts need bilingual review.',
                           'No repeated test-driven tuning was performed.']}
    (EXPERIMENT/'decision.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
