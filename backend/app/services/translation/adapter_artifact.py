"""Load only a locally evaluated, hash-matched, pair-scoped adapter artifact."""
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]


def _passes(domain,news,base_domain,base_news):
    for scores in (domain,news,base_domain,base_news):
        if any(not isinstance(scores[key],(int,float)) or not math.isfinite(scores[key])
               for key in ('bleu','chrf_plus_plus','inference_failures')):
            return False
    return (domain['chrf_plus_plus']>=base_domain['chrf_plus_plus']+0.5 and domain['bleu']>=base_domain['bleu']
            and news['chrf_plus_plus']>=base_news['chrf_plus_plus']-0.5
            and domain['inference_failures']<=base_domain['inference_failures']
            and news['inference_failures']<=base_news['inference_failures'])


def validated_artifact(decision_path,base_model,base_revision,root=ROOT):
    root=Path(root).resolve()
    path=Path(decision_path)
    if not path.is_absolute(): path=root/path
    path=path.resolve()
    if not path.is_relative_to(root): raise ValueError('Adapter decision must be inside the project')
    decision=json.loads(path.read_text(encoding='utf-8'))
    if decision.get('complete') is not True or decision.get('promotion_recommended') is not True:
        raise ValueError('Adapter has not passed promotion gates')
    selection=decision['selection']
    if selection.get('validation_gate_passed') is not True or decision.get('scope')!=['bengali','marathi']:
        raise ValueError('Adapter validation/scope is unsupported')
    if not _passes(selection['selected']['domain'],selection['selected']['news'],selection['baseline_domain'],selection['baseline_news']):
        raise ValueError('Adapter validation scores fail the gates')
    if not _passes(decision['test_candidate']['domain'],decision['test_candidate']['news'],
                   decision['test_baseline']['domain'],decision['test_baseline']['news']):
        raise ValueError('Adapter test scores fail the gates')
    checkpoint=(root/selection['selected']['checkpoint']).resolve()
    if not checkpoint.is_relative_to(root): raise ValueError('Checkpoint escapes the project')
    weights=checkpoint/'adapter_model.safetensors'
    digest=hashlib.sha256(weights.read_bytes()).hexdigest()
    if digest!=selection['adapter_sha256']: raise ValueError('Adapter checksum mismatch')
    config=json.loads((checkpoint.parent/'training_config.json').read_text(encoding='utf-8'))
    if config['base_model']!=base_model or config['base_revision']!=base_revision:
        raise ValueError('Adapter/base checkpoint mismatch')
    return checkpoint,digest
