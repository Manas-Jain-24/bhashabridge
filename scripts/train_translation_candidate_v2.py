"""Controlled Bengali→Marathi LoRA training on the frozen BPCC-pivot v2 corpus."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from prepare_translation_quality_v2 import OUT,audit,read
from translation_training_artifacts import experiment_directory,save_epoch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--rank',type=int,default=8)
    parser.add_argument('--learning-rate',type=float,default=0.00005)
    parser.add_argument('--epochs',type=int,default=2)
    parser.add_argument('--batch-size',type=int,default=4)
    parser.add_argument('--accumulation',type=int,default=4)
    parser.add_argument('--max-length',type=int,default=128)
    args=parser.parse_args()
    if min(args.rank,args.epochs,args.batch_size,args.accumulation)<1 or args.learning_rate<=0: parser.error('Invalid training parameters')
    args.output=experiment_directory(args.output,ROOT)
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    from peft import LoraConfig,TaskType,get_peft_model
    from app.services.translation.indictrans2 import IndicTrans2Adapter
    from app.services.translation.indic_processor import IndicScriptProcessor
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required')
    audit(); torch.set_num_threads(4); torch.manual_seed(42); random.seed(42)
    if (args.output/'training_config.json').exists(): raise ValueError('Existing experiment; choose a new directory')
    args.output.mkdir(parents=True,exist_ok=True)
    translator=IndicTrans2Adapter(allow_adapters=False)
    if not translator._lazy_load_model(): raise RuntimeError('Base model unavailable')
    tokenizer=translator.tokenizer; processor=IndicScriptProcessor(inference=False)
    encoded=[]; excluded=[]
    for row in read(OUT/'train.jsonl'):
        source=processor.preprocess_batch([row['source_text']],'ben_Beng','mar_Deva')[0]
        target=processor.preprocess_batch([row['target_text']],'mar_Deva','ben_Beng',is_target=True)[0]
        src=tokenizer(source,truncation=False,padding=False)
        with tokenizer.as_target_tokenizer(): target_ids=tokenizer(target,truncation=False,padding=False)['input_ids']
        if max(len(src['input_ids']),len(target_ids))>args.max_length: excluded.append(row['id']); continue
        encoded.append((row['id'],src,target_ids))
    if len(encoded)<5000: raise ValueError('Fewer than 5,000 usable training pairs; refusing a smaller run without a new protocol')
    base=translator.model
    if hasattr(base,'set_label_smoothing'): base.set_label_smoothing(0.0)
    model=get_peft_model(base,LoraConfig(task_type=TaskType.SEQ_2_SEQ_LM,r=args.rank,lora_alpha=2*args.rank,
                                       lora_dropout=0.05,target_modules=['q_proj','v_proj'],bias='none'))
    params=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(params,lr=args.learning_rate,weight_decay=0.01)
    scaler=torch.amp.GradScaler('cuda')
    config={'seed':42,'rank':args.rank,'alpha':2*args.rank,'learning_rate':args.learning_rate,'epochs':args.epochs,
            'batch_size':args.batch_size,'accumulation':args.accumulation,'effective_batch_size':args.batch_size*args.accumulation,
            'max_length':args.max_length,'target_modules':['q_proj','v_proj'],'dropout':0.05,
            'training_examples':len(encoded),'excluded_long_examples':excluded,
            'trainable_parameters':sum(p.numel() for p in params),'base_model':translator.model_checkpoint,
            'base_revision':getattr(base.config,'_commit_hash',None),'processor_version':processor.VERSION,
            'torch_version':torch.__version__,'device':torch.cuda.get_device_name(0),
            'training_data_sha256':hashlib.sha256((OUT/'train.jsonl').read_bytes()).hexdigest(),
            'drafts_used':False,'test_used_for_gradients':False,
            'alignment':'Upstream human English translations joined by exact shared source; no direct local human approval'}
    (args.output/'training_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print(json.dumps(config),flush=True)
    start=time.monotonic(); history=[]
    for epoch in range(args.epochs):
        random.shuffle(encoded); model.train(); optimizer.zero_grad(set_to_none=True)
        total_loss=0.; tokens=0; steps=0; batches=math.ceil(len(encoded)/args.batch_size)
        for batch_index in range(batches):
            batch=encoded[batch_index*args.batch_size:(batch_index+1)*args.batch_size]
            inputs=tokenizer.pad([item[1] for item in batch],padding=True,return_tensors='pt').to('cuda')
            labels=torch.full((len(batch),max(len(item[2]) for item in batch)),-100,dtype=torch.long,device='cuda')
            for i,item in enumerate(batch): labels[i,:len(item[2])]=torch.tensor(item[2],device='cuda')
            with torch.autocast('cuda',dtype=torch.float16): loss=model(**inputs,labels=labels,use_cache=False).loss
            if not torch.isfinite(loss): raise RuntimeError('Non-finite loss')
            group=(batch_index//args.accumulation)*args.accumulation
            divisor=min(args.accumulation,batches-group)
            scaler.scale(loss/divisor).backward()
            count=int((labels!=-100).sum()); total_loss+=loss.item()*count; tokens+=count
            if (batch_index+1)%args.accumulation==0 or batch_index+1==batches:
                scaler.unscale_(optimizer); torch.nn.utils.clip_grad_norm_(params,1.0)
                scaler.step(optimizer); scaler.update(); optimizer.zero_grad(set_to_none=True); steps+=1
            if (batch_index+1)%100==0:
                print(f'epoch {epoch+1}: batch {batch_index+1}/{batches} token_loss={total_loss/tokens:.4f} elapsed={time.monotonic()-start:.1f}s',flush=True)
        checkpoint=save_epoch(model,args.output,epoch+1,ROOT)
        history.append({'epoch':epoch+1,'mean_training_token_loss':total_loss/tokens,'optimizer_steps':steps,
                        'checkpoint':checkpoint,'elapsed_seconds':time.monotonic()-start})
        print(json.dumps(history[-1]),flush=True)
    report={'complete':True,'configuration':config,'history':history,'elapsed_seconds':time.monotonic()-start,
            'peak_gpu_memory_bytes':torch.cuda.max_memory_allocated(),'status':'awaiting_validation_selection'}
    (args.output/'training_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__': main()
