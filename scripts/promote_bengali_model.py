"""Export Bengali inference weights only when held-out validation beats the baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir',type=Path,default=ROOT/'ml/experiments/bengali-v1')
    args=parser.parse_args()
    import torch
    weights=args.model_dir/'weights/seq2seq_translit.pt'; vocab=args.model_dir/'vocab.json'
    report=json.loads((args.model_dir/'validation_evaluation.json').read_text(encoding='utf-8'))
    if report['split']!='validation' or report['examples']!=2500 or not report['promotion_eligible']:
        raise ValueError('Full Bengali validation must beat the existing fallback on exact match and CER')
    if digest(weights)!=report['weights_sha256'] or digest(vocab)!=report['vocab_sha256']:
        raise ValueError('Weights or vocabulary changed after evaluation')
    validation=ROOT/'data/processed/expanded/transliteration/validation.jsonl'
    if digest(validation)!=report['test_sha256']: raise ValueError('Validation corpus changed')
    checkpoint=torch.load(weights,map_location='cpu',weights_only=True)
    output=ROOT/'ml/models/bengali-v1'; output.mkdir(parents=True,exist_ok=True)
    torch.save({'model_state_dict':checkpoint['model_state_dict'],'hyperparams':checkpoint['hyperparams'],'epoch':checkpoint['epoch']},output/'inference.pt')
    shutil.copy2(vocab,output/'vocab.json')
    approval={'enabled':True,'language':'bengali','direction':'roman_to_native','status':'experimental',
              'promoted_at_utc':datetime.now(timezone.utc).isoformat(),'selection_split':'validation',
              'weights_sha256':digest(output/'inference.pt'),'vocab_sha256':digest(output/'vocab.json'),
              'validation_neural':report['neural'],'validation_baseline':report['current_app_fallback'],
              'license':'CC-BY-SA-4.0','source':'Google Dakshina v1.0; see data/README.md',
              'note':'Validation improvement is relative; absolute exact match is limited. Lexical and common-word mappings take precedence.'}
    (output/'promotion.json').write_text(json.dumps(approval,indent=2),encoding='utf-8')
    print(json.dumps(approval,indent=2))


if __name__=='__main__': main()
