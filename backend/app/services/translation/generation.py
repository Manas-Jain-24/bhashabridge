"""Avoid materializing unused prefix vocabulary logits during generation.

IndicTrans2's legacy forward projects every decoder position when cache is off.
Generation consumes only the last position. Slice immediately before the output
linear layer, leaving decoder states, weights, beam search and cache settings alone.
Call while holding the adapter's inference lock; always remove the temporary hook.
"""
import re

GENERATION_SETTINGS={'max_length':256,'num_beams':5,'use_cache':False,'no_repeat_ngram_size':4,'early_stopping':True}


class RepetitiveGenerationError(ValueError):
    pass


class OutputArtifactError(ValueError):
    pass


def validate_native_output(text, source_text=''):
    if not text.strip(): raise ValueError('Neural model returned empty text')
    if re.search(r'(.{3,40})\1{3,}',text):
        raise RepetitiveGenerationError('Neural model returned a degenerate repeated fragment')
    placeholders=re.findall(r'[<\[]\s*id\s*\d+\s*[>\]]', text, re.IGNORECASE)
    unknown=any(marker not in source_text for marker in placeholders)
    if unknown or (len(re.findall(r'ω\s*\d+',text))>=3 and 'ω' not in source_text):
        raise OutputArtifactError('Neural model returned unresolved placeholders')
    return text


def generate_next_token_scores(model, **kwargs):
    getter=getattr(model,'get_output_embeddings',None)
    head=getter() if getter is not None else None
    hook=None
    if head is not None and hasattr(head,'register_forward_pre_hook') and not getattr(model,'training',False):
        def last_position(module,inputs):
            return (inputs[0][:,-1:,:],*inputs[1:]) if inputs and inputs[0].ndim==3 else inputs
        hook=head.register_forward_pre_hook(last_position)
    try:
        return model.generate(**kwargs)
    finally:
        if hook is not None: hook.remove()
