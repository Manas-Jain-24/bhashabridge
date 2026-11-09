import pytest
from app.services.translation.generation import validate_native_output


def test_degenerate_generation_is_rejected_without_rejecting_normal_repetition():
    with pytest.raises(ValueError): validate_native_output('उन्होंने कहा: '+'डायोक्स-'*12)
    assert validate_native_output('আমি ভালো আছি। তুমিও ভালো আছো।')
    assert validate_native_output('हाँ, हाँ। ठीक है।')


def test_generation_projection_preserves_last_logits_and_restores_head():
    torch=pytest.importorskip('torch')
    from app.services.translation.generation import generate_next_token_scores
    torch.manual_seed(5)
    class Model:
        training=False
        def __init__(self): self.head=torch.nn.Linear(12,23)
        def get_output_embeddings(self): return self.head
        def generate(self,states,fail=False):
            result=self.head(states)
            if fail: raise RuntimeError('simulated generation failure')
            return result
    model=Model(); states=torch.randn(3,11,12)
    original=model.head(states)
    optimized=generate_next_token_scores(model,states=states)
    assert optimized.shape==(3,1,23)
    assert torch.allclose(optimized[:,0],original[:,-1],atol=1e-6)
    assert model.head(states).shape==(3,11,23)
    with pytest.raises(RuntimeError): generate_next_token_scores(model,states=states,fail=True)
    assert model.head(states).shape==(3,11,23)


@pytest.mark.parametrize('bad_output',['डायोक्स-'*12,'मूल्य <ID2> है।'])
def test_repetitive_bengali_translation_returns_quality_error(monkeypatch,bad_output):
    import sys
    from contextlib import nullcontext
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.services.translation.indictrans2 import IndicTrans2Adapter
    class Encoding(dict):
        def to(self,device): return self
    class Tokenizer:
        def __call__(self,*args,**kwargs): return Encoding(input_ids=[1])
        def batch_decode(self,*args,**kwargs): return [bad_output]
    class Model:
        def parameters(self): yield SimpleNamespace(device='cpu')
        def generate(self,**kwargs): return [1]
    class Processor:
        def preprocess_batch(self,texts,**kwargs): return texts
        def postprocess_batch(self,texts,**kwargs): return texts
    adapter=IndicTrans2Adapter(); adapter.is_loaded=True
    adapter.model,adapter.tokenizer,adapter.processor=Model(),Tokenizer(),Processor()
    monkeypatch.setattr(adapter,'_lazy_load_model',lambda:True)
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(no_grad=nullcontext))
    with pytest.raises(HTTPException) as failure:
        adapter.translate('আমি ভালো আছি।','bengali','hindi','native')
    assert failure.value.status_code==503 and 'reliable translation' in failure.value.detail
