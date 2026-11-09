"""Train an experimental Bengali→Marathi LoRA using only non-benchmark references."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from prepare_translation_quality import OUT, audit, keys, read
from translation_training_artifacts import experiment_directory,save_epoch
from app.services.translation.corpus import normalize_source


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs',type=int,default=2)
    parser.add_argument('--max-length',type=int,default=128)
    parser.add_argument('--output',type=Path,default=ROOT/'ml/experiments/translation-lora-v1')
    parser.add_argument('--learning-rate',type=float,default=0.0001)
    args=parser.parse_args()
    if args.epochs<1 or args.max_length<16: parser.error('Invalid epochs/length')
    args.output=experiment_directory(args.output,ROOT)
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    from peft import LoraConfig, TaskType, get_peft_model
    from app.services.translation.indictrans2 import IndicTrans2Adapter
    from app.services.translation.indic_processor import IndicScriptProcessor
    if not torch.cuda.is_available(): raise RuntimeError('CUDA is required for this local training recipe')
    torch.set_num_threads(4); torch.manual_seed(42); random.seed(42)
    audit()
    corrections=ROOT/'data/curated/translation_corrections_v1.jsonl'
    rows=read(OUT/'train.jsonl')+read(corrections)
    protected=keys(read(OUT/'validation.jsonl')+read(OUT/'test.jsonl')+read(ROOT/'data/processed/expanded/translation/test.jsonl'))
    legacy=read(ROOT/'data/processed/translation/test.jsonl')
    protected.update((lang,normalize_source(r[lang])) for r in legacy for lang in ('hindi','marathi'))
    for row in rows:
        for side in ('source','target'):
            if (row[f'{side}_language'],normalize_source(row[f'{side}_text'])) in protected:
                raise ValueError('Training/held-out overlap: '+row['id'])
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'training_report.json').exists(): raise ValueError('Experiment already finished; choose a new directory')
    adapter=IndicTrans2Adapter(allow_adapters=False)
    if not adapter._lazy_load_model(): raise RuntimeError('Base model unavailable')
    tokenizer=adapter.tokenizer
    processor=IndicScriptProcessor(inference=False)
    examples=[]; excluded=[]
    for row in rows:
        source=processor.preprocess_batch([row['source_text']],'ben_Beng','mar_Deva')[0]
        target=processor.preprocess_batch([row['target_text']],'mar_Deva','ben_Beng',is_target=True)[0]
        encoded=tokenizer(source,truncation=False,padding=False)
        with tokenizer.as_target_tokenizer(): labels=tokenizer(target,truncation=False,padding=False)['input_ids']
        if max(len(encoded['input_ids']),len(labels))>args.max_length:
            excluded.append(row['id']); continue
        examples.append((row['id'],encoded,labels))
    if not examples: raise RuntimeError('No usable training examples')
    base=adapter.model
    if hasattr(base,'set_label_smoothing'): base.set_label_smoothing(0.0)
    model=get_peft_model(base,LoraConfig(task_type=TaskType.SEQ_2_SEQ_LM,r=8,lora_alpha=16,
                         lora_dropout=0.05,target_modules=['q_proj','v_proj'],bias='none'))
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=args.learning_rate,weight_decay=0.01)
    scaler=torch.amp.GradScaler('cuda')
    trainable=sum(p.numel() for p in params)
    config={'seed':42,'epochs':args.epochs,'max_length':args.max_length,'learning_rate':args.learning_rate,
            'micro_batch_size':1,'gradient_accumulation':8,'rank':8,'alpha':16,'dropout':0.05,
            'target_modules':['q_proj','v_proj'],'training_examples':len(examples),'excluded_long_examples':excluded,
            'base_model':adapter.model_checkpoint,'base_revision':getattr(base.config,'_commit_hash',None),
            'processor_version':processor.VERSION,'trainable_parameters':trainable,
            'torch_version':torch.__version__,'device':torch.cuda.get_device_name(0),
            'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (OUT/'train.jsonl',corrections,OUT/'validation.jsonl',OUT/'test.jsonl')},
            'held_out_data_used_for_gradients':False,
            'limitations':['Small experimental adaptation; not a new general-purpose model.',
                           '94 locally authored correction drafts are not native-speaker reviewed.',
                           'Long examples are excluded, never silently truncated.']}
    (args.output/'training_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print(json.dumps(config),flush=True)
    start=time.monotonic(); history=[]
    for epoch in range(args.epochs):
        model.train(); random.shuffle(examples); optimizer.zero_grad(set_to_none=True)
        loss_total=0.; steps=0
        for index,(_,encoded,labels) in enumerate(examples):
            inputs={key:torch.tensor([value],device='cuda') for key,value in encoded.items() if key in ('input_ids','attention_mask')}
            inputs['labels']=torch.tensor([labels],device='cuda')
            with torch.autocast('cuda',dtype=torch.float16):
                output=model(**inputs,use_cache=False)
                loss=output.loss
            if not torch.isfinite(loss): raise RuntimeError('Non-finite training loss; experiment not publishable')
            # Scale the final partial accumulation group by its actual size.
            group_start=(index//8)*8
            divisor=min(8,len(examples)-group_start)
            scaler.scale(loss/divisor).backward()
            loss_total+=loss.item()
            if (index+1)%8==0 or index+1==len(examples):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(params,1.0)
                scaler.step(optimizer); scaler.update(); optimizer.zero_grad(set_to_none=True); steps+=1
            if (index+1)%100==0:
                print(f'epoch {epoch+1}: {index+1}/{len(examples)} loss={loss_total/(index+1):.4f} elapsed={time.monotonic()-start:.1f}s',flush=True)
        checkpoint=save_epoch(model,args.output,epoch+1,ROOT)
        history.append({'epoch':epoch+1,'mean_training_loss':loss_total/len(examples),'optimizer_steps':steps,
                        'checkpoint':checkpoint,'elapsed_seconds':time.monotonic()-start})
        print(json.dumps(history[-1]),flush=True)
    report={'complete':True,'configuration':config,'history':history,'elapsed_seconds':time.monotonic()-start,
            'peak_gpu_memory_bytes':torch.cuda.max_memory_allocated(),
            'status':'experimental_not_selected; validation and untouched test required'}
    (args.output/'training_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__': main()
