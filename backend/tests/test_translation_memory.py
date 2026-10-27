import json
import sys
from collections import defaultdict
from types import SimpleNamespace

from app.models.entities import ReviewedTranslation
from app.services.translation.corpus import ROOT, normalize_source
from app.services.translation.indictrans2 import IndicTrans2Adapter
from app.services.translation.memory import lookup_reviewed, seed_reviewed_translations
from app.services.translation.service import translate_with_memory


def test_reviewed_memory_is_seeded_and_precedes_model(db_session, monkeypatch):
    rows = db_session.query(ReviewedTranslation).all()
    assert len(rows) >= 600
    assert seed_reviewed_translations(db_session) == 0
    assert db_session.query(ReviewedTranslation).count() == len(rows)

    from app.services.translation import service
    monkeypatch.setattr(service.translation_service, "translate", lambda **kwargs: (_ for _ in ()).throw(AssertionError("model called")))
    result = translate_with_memory(db_session, "नमस्ते!", "hindi", "marathi", "devanagari")
    assert result["translation_native"] == "नमस्कार!"
    assert result["model_source"] == "reviewed_database"


def test_ambiguous_curated_source_not_stored(db_session):
    dataset = json.loads((ROOT / "data/processed/learning/bhashabridge_learning.json").read_text(encoding="utf-8"))
    variants = defaultdict(set)
    originals = {}
    for row in dataset:
        key = normalize_source(row["hindi_devanagari"])
        variants[key].add(normalize_source(row["marathi_devanagari"]))
        originals[key] = row["hindi_devanagari"]
    ambiguous = next(key for key, values in variants.items() if len(values) > 1)
    assert lookup_reviewed(db_session, originals[ambiguous], "hindi", "marathi") is None


def test_neural_adapter_uses_official_processor_contract(monkeypatch):
    class FakeTensor(dict):
        def to(self, device):
            return self

    class FakeTokenizer:
        def __call__(self, prepared, **kwargs):
            assert prepared == ["prepared sentence"]
            return FakeTensor(input_ids=[1])

        def batch_decode(self, tokens, **kwargs):
            return ["raw target"]

    class FakeModel:
        def parameters(self):
            yield SimpleNamespace(device="cpu")

        def generate(self, **kwargs):
            return [1]

    class FakeProcessor:
        def preprocess_batch(self, texts, src_lang, tgt_lang):
            assert texts == ["नमस्ते!"]
            assert (src_lang, tgt_lang) == ("hin_Deva", "mar_Deva")
            return ["prepared sentence"]

        def postprocess_batch(self, decoded, lang):
            assert decoded == ["raw target"]
            assert lang == "mar_Deva"
            return ["नमस्कार!"]

    class NoGrad:
        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(no_grad=NoGrad))
    adapter = IndicTrans2Adapter()
    adapter.model = FakeModel()
    adapter.tokenizer = FakeTokenizer()
    adapter.processor = FakeProcessor()
    monkeypatch.setattr(adapter, "_lazy_load_model", lambda: True)
    result = adapter.translate("नमस्ते!", script="devanagari")
    assert result["translation_native"] == "नमस्कार!"
    assert result["engine"] == "indictrans2-320m-neural"
