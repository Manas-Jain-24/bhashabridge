"""Predeclared, validation-selected adaptation experiment; fresh tests are last."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
EXPERIMENT=ROOT/'ml/experiments/translation-quality-v2'
EVALUATION=ROOT/'ml/evaluation/quality-v2'
DATA=ROOT/'data/processed/translation-quality-v2'
PROFILES=[{'name':'rank8-lr5e-5','rank':8,'lr':0.00005,'epochs':2},
          {'name':'rank8-lr1e-4','rank':8,'lr':0.0001,'epochs':1},
          {'name':'rank16-lr5e-5','rank':16,'lr':0.00005,'epochs':1}]
PROTOCOL={'profiles':PROFILES,'selection':'highest validation-domain chrF++, with validation-news non-regression',
          'validation_gate':{'domain_chrf_gain':0.5,'bleu_loss_allowed':0,'news_chrf_loss_allowed':0.5,'extra_failures_allowed':0},
          'test_gate':{'domain_chrf_gain':0.5,'bleu_loss_allowed':0,'news_chrf_loss_allowed':0.5,'extra_failures_allowed':0},
          'test_used_for_selection':False,'raw_correction_drafts_in_training':False,
          'semantic_review':'Provisional AI review is diagnostic, not native-human certification.',
          'budget':'Four total training epochs: equal one-epoch ablations; a second epoch only for the conservative reference profile.'}


def run(*args): subprocess.run([sys.executable,'-u',*map(str,args)],cwd=ROOT,check=True)


def score(directory):
    report=json.loads((directory/'bengali-marathi.json').read_text(encoding='utf-8'))
    if not report['complete'] or len(report['predictions'])!=report['identity']['examples']: raise ValueError('Incomplete evaluation')
    return {key:report[key] for key in ('bleu','chrf_plus_plus','inference_failures')}


def passes(domain,news,base_domain,base_news):
    return (domain['chrf_plus_plus']>=base_domain['chrf_plus_plus']+0.5 and domain['bleu']>=base_domain['bleu']
            and news['chrf_plus_plus']>=base_news['chrf_plus_plus']-0.5
            and domain['inference_failures']<=base_domain['inference_failures']
            and news['inference_failures']<=base_news['inference_failures'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-for-first',action='store_true',help='Wait for the already-running first training profile')
    args=parser.parse_args()
    EXPERIMENT.mkdir(parents=True,exist_ok=True); EVALUATION.mkdir(parents=True,exist_ok=True)
    protocol=EXPERIMENT/'protocol.json'
    if protocol.exists() and json.loads(protocol.read_text())!=PROTOCOL: raise ValueError('Frozen protocol changed')
    protocol.write_text(json.dumps(PROTOCOL,indent=2),encoding='utf-8')
    if args.wait_for_first:
        deadline=time.monotonic()+7200
        marker=ROOT/'.demo/quality-v2-train-a.exit'
        while not ((EXPERIMENT/PROFILES[0]['name']/'training_report.json').exists() and marker.exists() and marker.read_text().strip()=='0'):
            marker=ROOT/'.demo/quality-v2-train-a.exit'
            if marker.exists() and marker.read_text().strip()!='0': raise RuntimeError('First training profile failed')
            if time.monotonic()>deadline: raise RuntimeError('First training profile timed out')
            time.sleep(10)
    # A complete report is required before proceeding to another profile.
    for profile in PROFILES:
        destination=EXPERIMENT/profile['name']
        if not (destination/'training_report.json').exists():
            run('scripts/train_translation_candidate_v2.py','--output',destination,'--rank',profile['rank'],
                '--learning-rate',profile['lr'],'--epochs',profile['epochs'])
        report=json.loads((destination/'training_report.json').read_text())
        if not report['complete']: raise ValueError('Incomplete profile')
        config=report['configuration']
        if config['rank']!=profile['rank'] or config['learning_rate']!=profile['lr'] or config['epochs']!=profile['epochs']:
            raise ValueError('Training report does not match the frozen profile')
        if config['training_data_sha256']!=hashlib.sha256((DATA/'train.jsonl').read_bytes()).hexdigest():
            raise ValueError('Candidate used different training data')
    def evaluate(split,label,adapter=None):
        command=['scripts/evaluate_translation_quality.py','--data-dir',DATA,'--pair-only','--split',split,'--output',EVALUATION/label]
        if adapter: command.extend(['--adapter',adapter])
        run(*command)
        return score(EVALUATION/label)
    baseline_domain=evaluate('validation','validation-baseline')
    baseline_news=evaluate('validation_news','validation-news-baseline')
    candidates=[]
    for profile in PROFILES:
        for epoch in range(1,profile['epochs']+1):
            label=f'{profile["name"]}-epoch-{epoch}'; checkpoint=EXPERIMENT/profile['name']/f'epoch-{epoch}'
            domain=evaluate('validation','validation-'+label,checkpoint)
            news=evaluate('validation_news','validation-news-'+label,checkpoint)
            candidates.append({'label':label,'checkpoint':checkpoint.relative_to(ROOT).as_posix(),
                               'domain':domain,'news':news,'gate_passed':passes(domain,news,baseline_domain,baseline_news)})
    eligible=[row for row in candidates if row['gate_passed']]
    # Even a rejected experiment receives one final diagnostic test, without
    # changing its eligibility or choosing a different candidate from test scores.
    best=max(eligible or candidates,key=lambda row:(row['domain']['chrf_plus_plus'],row['news']['chrf_plus_plus'],row['domain']['bleu']))
    selection={'protocol':PROTOCOL,'baseline_domain':baseline_domain,'baseline_news':baseline_news,'candidates':candidates,
               'selected':best,'validation_gate_passed':bool(eligible),
               'adapter_sha256':hashlib.sha256((ROOT/best['checkpoint']/'adapter_model.safetensors').read_bytes()).hexdigest(),
               'data_manifest_sha256':hashlib.sha256((DATA/'manifest.json').read_bytes()).hexdigest()}
    path=EXPERIMENT/'selection.json'
    if path.exists() and json.loads(path.read_text())!=selection: raise ValueError('Frozen selection changed after testing')
    path.write_text(json.dumps(selection,indent=2),encoding='utf-8')
    print('VALIDATION_SELECTION_FROZEN',json.dumps(selection),flush=True)
    base_domain=evaluate('test','test-baseline'); base_news=evaluate('test_news','test-news-baseline')
    candidate_domain=evaluate('test','test-candidate',ROOT/best['checkpoint'])
    candidate_news=evaluate('test_news','test-news-candidate',ROOT/best['checkpoint'])
    result={'complete':True,'selection':selection,'test_baseline':{'domain':base_domain,'news':base_news},
            'test_candidate':{'domain':candidate_domain,'news':candidate_news},
            'promotion_recommended':bool(eligible) and passes(candidate_domain,candidate_news,base_domain,base_news),
            'scope':['bengali','marathi'],'human_approved_direct_pairs':0,
            'limitations':['BPCC may be present in base-model pretraining.','Fresh NTREX means unused in local adaptation; upstream exposure unknown.',
                           'No broad accuracy percentage or native-human certification is established.']}
    (EXPERIMENT/'decision.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
