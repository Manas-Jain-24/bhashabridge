"""Opt-in streamed loading for cached Safetensors on memory-constrained Windows.

Uses the documented Safetensors header/offset format. Reads bounded chunks instead
of mapping the entire 1.28 GB checkpoint into the Windows commit budget.
"""
import json
import math
import logging
from pathlib import Path


def read_state(path, dtype):
    import torch
    types={'F32':torch.float32,'F16':torch.float16,'BF16':torch.bfloat16,'I64':torch.int64,'I32':torch.int32,'BOOL':torch.bool}
    state={}
    with Path(path).open('rb') as stream:
        length=int.from_bytes(stream.read(8),'little')
        if not 2<=length<=16*1024*1024: raise ValueError('Invalid Safetensors header length')
        header=json.loads(stream.read(length))
        data_start=8+length; file_size=Path(path).stat().st_size
        for name,spec in header.items():
            if name=='__metadata__': continue
            source_dtype=types[spec['dtype']]
            size=torch.empty((),dtype=source_dtype).element_size()
            start,end=spec['data_offsets']; shape=spec['shape']; count=math.prod(shape)
            if start<0 or end<start or data_start+end>file_size or end-start!=count*size:
                raise ValueError('Invalid tensor offsets or shape')
            target_dtype=dtype if source_dtype.is_floating_point else source_dtype
            tensor=torch.empty(shape,dtype=target_dtype)
            flat=tensor.reshape(-1); stream.seek(data_start+start)
            chunk_elements=max(1,1024*1024//size)
            for index in range(0,count,chunk_elements):
                n=min(chunk_elements,count-index)
                payload=bytearray(stream.read(n*size))
                if len(payload)!=n*size: raise ValueError('Truncated tensor')
                flat[index:index+n].copy_(torch.frombuffer(payload,dtype=source_dtype))
            state[name]=tensor
            if len(state)%50==0: logging.getLogger(__name__).info('Streamed %s checkpoint tensors',len(state))
    return state


def load_streamed(checkpoint,dtype):
    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoConfig,AutoModelForSeq2SeqLM,GenerationConfig
    config=AutoConfig.from_pretrained(checkpoint,trust_remote_code=True,local_files_only=True)
    weights=hf_hub_download(checkpoint,'model.safetensors',local_files_only=True)
    with torch.device('meta'):
        model=AutoModelForSeq2SeqLM.from_config(config,trust_remote_code=True,dtype=dtype)
    logging.getLogger(__name__).info('Model skeleton ready; streaming cached checkpoint')
    state=read_state(weights,dtype)
    result=model.load_state_dict(state,strict=False,assign=True)
    if result.unexpected_keys: raise ValueError('Unexpected checkpoint weights')
    model.tie_weights()
    if any(p.is_meta for p in model.parameters()): raise ValueError('Checkpoint did not initialize every model parameter')
    # Some transformer modules use nonpersistent scalar buffers only as device/dtype markers.
    for module in model.modules():
        for name,buffer in list(module._buffers.items()):
            if buffer is not None and buffer.is_meta:
                if name not in module._non_persistent_buffers_set: raise ValueError('Missing persistent buffer')
                module._buffers[name]=torch.zeros(buffer.shape,dtype=buffer.dtype)
    model.generation_config=GenerationConfig.from_pretrained(checkpoint,local_files_only=True)
    return model
