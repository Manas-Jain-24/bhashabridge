"""Lazy, checksum-verified Bengali word model. Dependencies remain optional."""
import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path
import threading

ROOT=Path(__file__).resolve().parents[4]
ARTIFACT=ROOT/'ml/models/bengali-v1'
_load_lock=threading.Lock()
_inference_lock=threading.Lock()
_predictor=None
_failed=False


def _load():
    global _predictor,_failed
    if _predictor is not None or _failed: return _predictor
    with _load_lock:
        if _predictor is not None or _failed: return _predictor
        try:
            approval=json.loads((ARTIFACT/'promotion.json').read_text(encoding='utf-8'))
            if not approval['enabled'] or approval['selection_split']!='validation': raise ValueError('Unapproved model')
            for name,key in [('inference.pt','weights_sha256'),('vocab.json','vocab_sha256')]:
                if hashlib.sha256((ARTIFACT/name).read_bytes()).hexdigest()!=approval[key]: raise ValueError('Artifact checksum mismatch')
            import torch
            from ml.transliteration.model import Encoder,Decoder,Seq2Seq
            from ml.transliteration.dataset import CharVocab
            vocab=json.loads((ARTIFACT/'vocab.json').read_text(encoding='utf-8'))
            src=CharVocab.from_dict(vocab['src_vocab']); tgt=CharVocab.from_dict(vocab['tgt_vocab'])
            checkpoint=torch.load(ARTIFACT/'inference.pt',map_location='cpu',weights_only=True)
            hp=checkpoint['hyperparams']
            if hp.get('language')!='bengali' or not hp.get('packed_encoder'): raise ValueError('Incompatible model')
            model=Seq2Seq(Encoder(len(src),hp['emb_dim'],hp['enc_hid_dim'],hp['dec_hid_dim'],packed=True),Decoder(len(tgt),hp['emb_dim'],hp['enc_hid_dim'],hp['dec_hid_dim']))
            model.load_state_dict(checkpoint['model_state_dict']); model.eval()
            _predictor=(model,src,tgt)
        except Exception as exc:
            _failed=True
            logging.getLogger(__name__).info('Bengali neural model unavailable (%s); using phonetic rules',type(exc).__name__)
        return _predictor


@lru_cache(maxsize=4096)
def predict_word(word):
    from app.core.config import settings
    if settings.TESTING or settings.USE_MOCK_MODELS or not settings.BENGALI_NEURAL_TRANSLITERATION: return None
    if not word.isascii() or not word.isalpha() or not 2<=len(word)<=32: return None
    predictor=_load()
    if predictor is None: return None
    import torch
    model,src,tgt=predictor
    try:
        with _inference_lock,torch.inference_mode():
            result=model.predict(torch.tensor([src.encode(word.lower())]),max_len=40)
        text=tgt.decode(result[0].tolist())
        return text if text and all('\u0980'<=c<='\u09ff' for c in text) else None
    except Exception as exc:
        logging.getLogger(__name__).info('Bengali inference failed (%s); using phonetic rules',type(exc).__name__)
        return None
