"""Evaluate a frozen fresh validation/test split with optional pair-scoped LoRA."""
import argparse
from contextlib import nullcontext
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from prepare_translation_quality import OUT,audit,read


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',choices=['validation','test'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--adapter',type=Path)
    parser.add_argument('--legacy-processor',action='store_true')
    parser.add_argument('--pair-only',action='store_true',help='Only evaluate the adapted Bengali→Marathi direction')
    parser.add_argument('--batch-size',type=int,default=16)
    args=parser.parse_args()
    if args.batch_size<1: parser.error('Batch size must be positive')
    if args.legacy_processor and args.adapter: parser.error('Adapters use the current processor')
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    from sacrebleu.metrics import BLEU,CHRF
    from app.services.translation.indictrans2 import IndicTrans2Adapter
    from app.services.translation.indic_processor import IndicScriptProcessor
    import app.services.translation.indictrans2 as module
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required')
    torch.set_num_threads(4); audit()
    translator=IndicTrans2Adapter()
    if not translator._lazy_load_model(): raise RuntimeError('Model unavailable')
    if args.legacy_processor:
        # Archived behavior of commit 8a93314, for validation comparisons only.
        class LegacyProcessor(IndicScriptProcessor):
            VERSION='windows-legacy-v1'
            def preprocess_batch(self,texts,src_lang,tgt_lang):
                source=self.CODES[src_lang]; normalizer=self._normalizers.get_normalizer(source)
                from indicnlp.tokenize import indic_tokenize
                return [f'{src_lang} {tgt_lang} '+self._transliterator.transliterate(
                    ' '.join(indic_tokenize.trivial_tokenize(normalizer.normalize(text.strip()),source)),source,'hi').replace(' ् ','्').strip()
                    for text in texts]
            def postprocess_batch(self,texts,lang):
                from indicnlp.tokenize import indic_detokenize
                target=self.CODES[lang]
                return [indic_detokenize.trivial_detokenize(self._transliterator.transliterate(text,'hi',target),target) for text in texts]
        translator.processor=LegacyProcessor()
        def legacy_guard(text,source_text=''):
            if not text.strip(): raise ValueError('Empty translation')
            if re.search(r'(.{3,40})\1{3,}',text):
                from app.services.translation.generation import RepetitiveGenerationError
                raise RepetitiveGenerationError('Repeated output')
            return text
        module.validate_native_output=legacy_guard
    adapter_hash=None
    if args.adapter:
        from peft import PeftModel
        adapter_hash=hashlib.sha256((args.adapter/'adapter_model.safetensors').read_bytes()).hexdigest()
        translator.model=PeftModel.from_pretrained(translator.model,args.adapter,is_trainable=False)
        translator.model.eval()
    rows=read(OUT/f'{args.split}.jsonl')
    args.output.mkdir(parents=True,exist_ok=True)
    pairs=[('bengali','marathi')] if args.pair_only else itertools.permutations(('hindi','marathi','bengali'),2)
    summary=[]
    for source,target in pairs:
        report_path=args.output/f'{source}-{target}.json'
        adapted=bool(args.adapter and (source,target)==('bengali','marathi'))
        identity={'split':args.split,'source':source,'target':target,'examples':len(rows),
                  'data_sha256':hashlib.sha256((OUT/f'{args.split}.jsonl').read_bytes()).hexdigest(),
                  'model':translator.model_checkpoint,'model_revision':getattr(translator.model.config,'_commit_hash',None),
                  'processor_version':translator.processor.VERSION,'adapter_sha256':adapter_hash if adapted else None,
                  'precision':'float16','batch_size':args.batch_size,'generation':module.GENERATION_SETTINGS,
                  'torch_version':torch.__version__,'device':torch.cuda.get_device_name(0)}
        previous=json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
        if previous and previous['identity']!=identity: raise ValueError('Incompatible saved evaluation')
        predictions=previous.get('predictions',[])
        if len(predictions)>len(rows) or any(
            p['id']!=row['id'] or p['source']!=row['sentences'][source] or p['reference']!=row['sentences'][target]
            for p,row in zip(predictions,rows)):
            raise ValueError('Saved predictions do not match the frozen corpus')
        if previous.get('complete'):
            if len(predictions)!=len(rows): raise ValueError('Incomplete saved coverage')
            summary.append({k:previous[k] for k in ('identity','bleu','chrf_plus_plus','inference_failures','elapsed_seconds')})
            print('Using complete saved report:',report_path,flush=True)
            continue
        elapsed=previous.get('elapsed_seconds',0); start=time.monotonic()
        for index in range(len(predictions),len(rows),args.batch_size):
            batch=rows[index:index+args.batch_size]; errors={}
            context=translator.model.disable_adapter() if args.adapter and not adapted else nullcontext()
            with context:
                try: texts=translator.translate_native_batch([r['sentences'][source] for r in batch],source,target)
                except Exception as batch_error:
                    print(f'{source}->{target} batch retry: {type(batch_error).__name__}',flush=True)
                    texts=[]
                    for i,row in enumerate(batch):
                        try: texts.append(translator.translate_native_batch([row['sentences'][source]],source,target)[0])
                        except Exception as exc: texts.append(''); errors[i]=type(exc).__name__
            predictions.extend({'id':row['id'],'source':row['sentences'][source],'reference':row['sentences'][target],
                                'prediction':text,**({'inference_error':errors[i]} if i in errors else {})}
                               for i,(row,text) in enumerate(zip(batch,texts)))
            report={'identity':identity,'complete':False,'predictions':predictions,
                    'elapsed_seconds':elapsed+time.monotonic()-start}
            temporary=report_path.with_suffix('.tmp'); temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); temporary.replace(report_path)
            print(f'{source}->{target}: {len(predictions)}/{len(rows)}',flush=True)
        bleu=BLEU(tokenize='intl'); chrf=CHRF(word_order=2)
        hypotheses=[r['prediction'] for r in predictions]; references=[[r['reference'] for r in predictions]]
        report={'identity':identity,'complete':True,'predictions':predictions,
                'bleu':bleu.corpus_score(hypotheses,references).score,'chrf_plus_plus':chrf.corpus_score(hypotheses,references).score,
                'bleu_signature':str(bleu.get_signature()),'chrf_signature':str(chrf.get_signature()),
                'inference_failures':sum('inference_error' in r for r in predictions),
                'elapsed_seconds':elapsed+time.monotonic()-start}
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        summary.append({k:report[k] for k in ('identity','bleu','chrf_plus_plus','inference_failures','elapsed_seconds')})
        print(json.dumps(summary[-1]),flush=True)
    result={'complete':True,'split':args.split,'examples_per_direction':len(rows),'directions':summary,
            'scope':'Frozen document-disjoint NTREX subset; not all NTREX or general accuracy.',
            'upstream_training_exposure':'unknown'}
    (args.output/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__': main()
