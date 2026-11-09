"""Recompute saved report scores after the shared, deterministic punctuation repair.

No model calls or reference-dependent repairs. Keeps the original processed string
when a prediction changes, and refuses incomplete reports.
"""
import json
import sys
import itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.services.translation.punctuation import finish_native_sentence,POSTPROCESSOR_VERSION
from sacrebleu.metrics import BLEU,CHRF
from app.core.languages import LANGUAGES


def main():
    directory=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'ml/evaluation/expanded-diagnostic'
    files=sorted(directory.glob('*-diagnostic-16.json'))
    expected=set(itertools.permutations(LANGUAGES,2))
    if len(files)!=len(expected): raise ValueError('Every language direction report is required')
    reports=[json.loads(p.read_text(encoding='utf-8')) for p in files]
    actual={(r['identity']['source_language'],r['identity']['target_language']) for r in reports}
    if actual!=expected: raise ValueError('Missing or duplicated language direction')
    common_keys=('model','model_revision','test_sha256','precision','processor','generation')
    configurations={json.dumps({k:r['identity'][k] for k in common_keys},sort_keys=True) for r in reports}
    if len(configurations)!=1: raise ValueError('Cannot combine different model, data or decoding configurations')
    summary=[]
    for path in files:
        report=json.loads(path.read_text(encoding='utf-8'))
        if not report.get('complete') or report['examples']!=16: raise ValueError('Incomplete diagnostic')
        changed=0
        for row in report['predictions']:
            fixed=finish_native_sentence(row['prediction'])
            if fixed!=row['prediction']:
                row['legacy_processed_prediction']=row['prediction']; row['prediction']=fixed; changed+=1
        bleu=BLEU(tokenize='intl'); chrf=CHRF(word_order=2)
        predictions=report['predictions']; references=[p['reference'] for p in predictions]
        old_predictions=[p.get('legacy_processed_prediction',p['prediction']) for p in predictions]
        report['scores_before_punctuation_repair']={'bleu':bleu.corpus_score(old_predictions,[references]).score,
                                                    'chrf_plus_plus':chrf.corpus_score(old_predictions,[references]).score}
        report['bleu']=bleu.corpus_score([p['prediction'] for p in predictions],[references]).score
        report['chrf_plus_plus']=chrf.corpus_score([p['prediction'] for p in predictions],[references]).score
        report['bleu_signature']=str(bleu.get_signature()); report['chrf_signature']=str(chrf.get_signature())
        report['lowest_scoring_examples']=sorted(({**p,'sentence_chrf_plus_plus':chrf.sentence_score(p['prediction'],[p['reference']]).score} for p in predictions),key=lambda p:p['sentence_chrf_plus_plus'])[:10]
        report['postprocessor']=POSTPROCESSOR_VERSION
        report['punctuation_repairs']=sum('legacy_processed_prediction' in p for p in predictions)
        report['sample_selection']='First 16 source-order rows. Small domain-biased diagnostic, not a representative quality estimate.'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        summary.append({'source':report['identity']['source_language'],'target':report['identity']['target_language'],
                        'examples':report['examples'],'bleu':report['bleu'],'chrf_plus_plus':report['chrf_plus_plus'],'punctuation_repairs':report['punctuation_repairs'],
                        'inference_failures':sum('inference_error' in p for p in predictions)})
    output={'complete':True,'diagnostic_subset':True,'examples_per_direction':16,'full_split_examples_per_direction':1012,
            'postprocessor':POSTPROCESSOR_VERSION,'configuration':json.loads(next(iter(configurations))),
            'sampling':'First 16 rows; no general translation-accuracy claim.','directions':summary}
    (directory/'summary.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output,indent=2))


if __name__=='__main__': main()
