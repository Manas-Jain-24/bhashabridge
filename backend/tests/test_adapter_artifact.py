from contextlib import contextmanager
import hashlib
import json

import pytest
from app.services.translation.adapter_artifact import validated_artifact
from app.services.translation.indictrans2 import IndicTrans2Adapter


def fixture_artifact(tmp_path):
    checkpoint=tmp_path/'profile/epoch-1'; checkpoint.mkdir(parents=True)
    weights=checkpoint/'adapter_model.safetensors'; weights.write_bytes(b'test-adapter')
    (checkpoint.parent/'training_config.json').write_text(json.dumps({'base_model':'base','base_revision':'r1'}))
    baseline={'bleu':20,'chrf_plus_plus':40,'inference_failures':0}
    better={'bleu':21,'chrf_plus_plus':41,'inference_failures':0}
    decision={'complete':True,'promotion_recommended':True,'scope':['bengali','marathi'],
              'selection':{'validation_gate_passed':True,'selected':{'checkpoint':'profile/epoch-1','domain':better,'news':baseline},
                           'baseline_domain':baseline,'baseline_news':baseline,
                           'adapter_sha256':hashlib.sha256(weights.read_bytes()).hexdigest()},
              'test_baseline':{'domain':baseline,'news':baseline},'test_candidate':{'domain':better,'news':baseline}}
    path=tmp_path/'decision.json'; path.write_text(json.dumps(decision))
    return path,checkpoint,decision


def test_validated_artifact_requires_real_gates_and_matching_bytes(tmp_path):
    path,checkpoint,_=fixture_artifact(tmp_path)
    assert validated_artifact(path,'base','r1',tmp_path)[0]==checkpoint
    (checkpoint/'adapter_model.safetensors').write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'): validated_artifact(path,'base','r1',tmp_path)


@pytest.mark.parametrize('problem',['not_promoted','wrong_scope','failed_test','wrong_base','escape'])
def test_unsafe_or_rejected_artifacts_cannot_be_loaded(tmp_path,problem):
    path,_,decision=fixture_artifact(tmp_path)
    base='base'
    if problem=='not_promoted': decision['promotion_recommended']=False
    elif problem=='wrong_scope': decision['scope']=['hindi','marathi']
    elif problem=='failed_test': decision['test_candidate']['domain']={'bleu':30,'chrf_plus_plus':39,'inference_failures':0}
    elif problem=='wrong_base': base='other'
    else: decision['selection']['selected']['checkpoint']='../elsewhere'
    path.write_text(json.dumps(decision))
    with pytest.raises(ValueError): validated_artifact(path,base,'r1',tmp_path)


def test_pair_scope_restores_base_adapter_state_after_errors():
    class Model:
        enabled=True
        @contextmanager
        def disable_adapter(self):
            self.enabled=False
            try: yield
            finally: self.enabled=True
    service=IndicTrans2Adapter(); service.model=Model(); service.adapter_sha256='test'
    with service._adapter_context('bengali','marathi'): assert service.model.enabled
    with pytest.raises(RuntimeError):
        with service._adapter_context('hindi','marathi'):
            assert not service.model.enabled
            raise RuntimeError('failed request')
    assert service.model.enabled
