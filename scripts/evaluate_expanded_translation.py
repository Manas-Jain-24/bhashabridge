"""Resumable native-script neural benchmark on held-out FLORES-200 devtest."""
import argparse
import json
import os
import sys
import itertools
import hashlib
import time
import logging
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def main():
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    from app.core.languages import LANGUAGES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=list(LANGUAGES))
    parser.add_argument("--target", choices=list(LANGUAGES))
    parser.add_argument("--all-pairs", action="store_true")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument('--precision',choices=['float32','float16','bfloat16'],default='float32')
    parser.add_argument('--stream-weights',action='store_true',help='Read cached weights in bounded chunks to reduce Windows memory-map commit')
    parser.add_argument('--verify-generation-parity',action='store_true',help='Compare two stored predictions per resumed direction after generation optimization')
    parser.add_argument("--output-dir", type=Path, default=ROOT/'ml/evaluation/expanded')
    parser.add_argument("--limit", type=int, default=0, help="0 evaluates the full split; smaller runs are diagnostic only")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument('--require-device', choices=['cpu', 'cuda'], help='Fail instead of benchmarking on a different device')
    args = parser.parse_args()
    if args.limit<0 or args.batch_size<1 or args.threads<1: parser.error('Invalid limit, batch size or threads')
    if not args.all_pairs and (not args.source or not args.target or args.source==args.target): parser.error('Choose --all-pairs or distinct source and target')
    if args.offline:
        os.environ["HF_HUB_OFFLINE"]="1"; os.environ["TRANSFORMERS_OFFLINE"]="1"
    from check_expanded_data import audit
    from sacrebleu.metrics import CHRF, BLEU
    from app.services.translation.indictrans2 import IndicTrans2Adapter
    from app.services.translation.punctuation import finish_native_sentence,POSTPROCESSOR_VERSION
    from app.services.translation.generation import GENERATION_SETTINGS
    import torch
    torch.set_num_threads(args.threads)
    logging.info('Auditing frozen expanded data')
    audit()
    logging.info('Loading neural checkpoint')
    translator=IndicTrans2Adapter(cpu_dtype=args.precision,stream_weights=args.stream_weights)
    if not translator._lazy_load_model(): raise RuntimeError('Neural model unavailable; fallback scores will not be published')
    device = next(translator.model.parameters()).device
    if args.require_device and device.type != args.require_device:
        raise RuntimeError(f'Required {args.require_device}, but model loaded on {device}')
    runtime = {'threads':args.threads,'batch_size':args.batch_size,'streamed_weights':args.stream_weights,
               'last_token_projection':True,'device':str(device),'torch_version':torch.__version__,
               'cuda_version':torch.version.cuda,
               'device_name':torch.cuda.get_device_name(device) if device.type=='cuda' else 'CPU'}
    logging.info('Inference runtime: %s', json.dumps(runtime))
    data_path=ROOT/'data/processed/expanded/translation/test.jsonl'
    rows=[json.loads(line) for line in data_path.read_text(encoding='utf-8').splitlines()]
    total=len(rows)
    if args.limit: rows=rows[:args.limit]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pairs=itertools.permutations(LANGUAGES,2) if args.all_pairs else [(args.source,args.target)]
    for source,target in pairs:
        name=f'{source}-{target}'+(f'-diagnostic-{len(rows)}' if len(rows)<total else '')
        output=args.output_dir/(name+'.json')
        identity={'source_language':source,'target_language':target,'test_sha256':hashlib.sha256(data_path.read_bytes()).hexdigest(),
                  'model':translator.model_checkpoint,'model_revision':getattr(translator.model.config,'_commit_hash',None),
                  'processor':type(translator.processor).__name__,'precision':str(next(translator.model.parameters()).dtype).replace('torch.',''),'generation':GENERATION_SETTINGS,
                  'requested_examples':len(rows),'test_source':'FLORES-200 devtest'}
        previous=json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
        if previous and previous.get('identity')!=identity: raise ValueError(f'Incompatible report: {output}')
        predictions=previous.get('predictions',[])
        parity=previous.get('generation_parity_verified',0)
        if args.verify_generation_parity and predictions:
            sample=predictions[:2]
            actual=translator.translate_native_batch([p['source'] for p in sample],source,target)
            if actual!=[finish_native_sentence(p['prediction']) for p in sample]:
                raise ValueError(f'Generation parity changed for {source}->{target}; investigate before publishing')
            parity=len(sample)
            logging.info('Exact saved-output parity verified: %s->%s (%s examples)',source,target,parity)
        elapsed=previous.get('elapsed_seconds',0); start=time.monotonic()
        for index in range(len(predictions),len(rows),args.batch_size):
            batch=rows[index:index+args.batch_size]
            errors={}
            try:
                translated=translator.translate_native_batch([r['sentences'][source] for r in batch],source,target)
            except Exception:
                translated=[]
                for i,row in enumerate(batch):
                    try: translated.append(translator.translate_native_batch([row['sentences'][source]],source,target)[0])
                    except Exception as exc:
                        translated.append(''); errors[i]=type(exc).__name__
            predictions.extend({'index':index+i,'source':row['sentences'][source],'reference':row['sentences'][target],'prediction':text,
                                **({'inference_error':errors[i]} if i in errors else {})} for i,(row,text) in enumerate(zip(batch,translated)))
            write_json(output,{**previous,'identity':identity,'complete':False,'diagnostic_subset':len(rows)<total,'examples':len(predictions),
                               'runtime_config':runtime,'elapsed_seconds':elapsed+time.monotonic()-start,'predictions':predictions})
            print(f'{source}->{target}: {len(predictions)}/{len(rows)} ({elapsed+time.monotonic()-start:.1f}s)',flush=True)
        for prediction in predictions:
            fixed=finish_native_sentence(prediction['prediction'])
            if fixed!=prediction['prediction']:
                prediction['legacy_processed_prediction']=prediction['prediction']; prediction['prediction']=fixed
        predicted=[p['prediction'] for p in predictions]; reference=[p['reference'] for p in predictions]
        bleu=BLEU(tokenize='intl'); chrf=CHRF(word_order=2)
        scores={'bleu':bleu.corpus_score(predicted,[reference]).score,'chrf_plus_plus':chrf.corpus_score(predicted,[reference]).score,
                'bleu_signature':str(bleu.get_signature()),'chrf_signature':str(chrf.get_signature())}
        errors=sorted(({**p,'sentence_chrf_plus_plus':chrf.sentence_score(p['prediction'],[p['reference']]).score} for p in predictions),key=lambda p:p['sentence_chrf_plus_plus'])[:10]
        write_json(output,{**previous,'identity':identity,'complete':True,'diagnostic_subset':len(rows)<total,'examples':len(predictions),
                           'postprocessor':POSTPROCESSOR_VERSION,'generation_parity_verified':parity,'inference_failures':sum('inference_error' in p for p in predictions),
                           'runtime_config':runtime,
                           'sample_selection':'Full split' if len(rows)==total else f'First {len(rows)} source-order rows; domain-biased diagnostic, not representative.',
                           'elapsed_seconds':elapsed+time.monotonic()-start,**scores,'lowest_scoring_examples':errors,'predictions':predictions,
                           'limitations':['Automatic similarity does not replace bilingual review.','Our teaching data is excluded; upstream pretrained-model exposure is unknown.','Native-script model path; reviewed-memory overrides and Roman input are not evaluated.']})
        print(json.dumps({'pair':name,'examples':len(predictions),**scores}),flush=True)


if __name__=='__main__':
    main()
