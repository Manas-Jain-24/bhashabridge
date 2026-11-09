"""Edge cases found during the multilingual bug pass."""
import json
from types import SimpleNamespace
import pytest
from app.services.translation.indictrans2 import IndicTrans2Adapter


@pytest.mark.parametrize("route,body", [
    ("analyze", {"text": "   "}),
    ("translate", {"text": "   "}),
    ("transliterate", {"text": "   "}),
])
def test_blank_text_rejected_before_model(client, route, body):
    assert client.post("/api/" + route, json=body).status_code == 422


@pytest.mark.parametrize("route", ["analyze", "translate"])
def test_wrong_source_script_returns_actionable_error(client, route):
    result = client.post("/api/" + route, json={"text": "আমি জল চাই।", "source_language": "hindi", "target_language": "marathi"})
    assert result.status_code == 422
    assert "script" in result.json()["detail"].lower()


@pytest.mark.parametrize("source", ["bengali", "auto"])
def test_analyze_never_silently_switches_explicit_target(client, source):
    result = client.post("/api/analyze", json={"text": "আমি জল চাই।", "source_language": source, "target_language": "bengali"})
    assert result.status_code == 422


def test_mixed_bengali_input_keeps_raw_text_alongside_native_guess(client, monkeypatch):
    from app.api.routes import analyze
    def translate(db, text, **kwargs):
        assert text == "আমি bangla shikhte chai।"
        assert kwargs['native_text'] == "আমি বাংলা শিখতে চাই।"
        return dict(translation="test",translation_native="मैं बंगाली सीखना चाहता हूँ।",translation_roman="test",english_meaning="")
    monkeypatch.setattr(analyze, "translate_with_memory", translate)
    result = client.post("/api/analyze", json={"text":"আমি bangla shikhte chai।", "source_language":"bengali", "target_language":"hindi"})
    assert result.status_code == 200


def test_cached_result_has_current_input_and_cannot_be_mutated():
    adapter = IndicTrans2Adapter()
    first = adapter.translate("Mujhe paani chahiye", "hindi", "marathi")
    first["translation_native"] = "CORRUPTED"
    second = adapter.translate("mujhe paani chahiye", "hindi", "marathi")
    assert second["source_text"] == "mujhe paani chahiye"
    assert second["translation_native"] != "CORRUPTED"


@pytest.mark.parametrize("payload", [
    {"summary": {"bad":"type"}, "differences":[]},
    {"summary":"text", "differences":"not a list"},
    {"summary":"text", "differences":[{"bad":"type"}]},
])
def test_malformed_tutor_json_does_not_escape_to_api(monkeypatch, payload):
    from app.services.explanation.llm_tutor import GeminiLinguisticTutor
    tutor = GeminiLinguisticTutor()
    monkeypatch.setattr(GeminiLinguisticTutor, "is_available", property(lambda self: True))
    tutor._client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
    assert tutor.explain("source", "bengali", "target", "hindi") is None


@pytest.mark.parametrize("word", ["vishesh", "wr", "vikas", "vishwa"])
def test_bengali_roman_fallback_never_emits_unassigned_unicode(word):
    import unicodedata
    from app.services.transliteration.service import transliteration_service
    result = transliteration_service.transliterate(word, "bengali", "latin_to_native")
    assert not any(unicodedata.category(c) == "Cn" for c in result)
    assert "ব" in result


def test_tutor_failure_uses_one_bounded_attempt(monkeypatch):
    from app.services.explanation.llm_tutor import GeminiLinguisticTutor
    tutor = GeminiLinguisticTutor()
    calls = []
    def unavailable(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("simulated outage")
    tutor._client = SimpleNamespace(models=SimpleNamespace(generate_content=unavailable))
    monkeypatch.setattr(GeminiLinguisticTutor, "is_available", property(lambda self: True))
    assert tutor.explain("source", "bengali", "target", "hindi") is None
    assert len(calls) == 1


def test_valid_tutor_json_is_preserved(monkeypatch):
    from app.services.explanation.llm_tutor import GeminiLinguisticTutor
    tutor = GeminiLinguisticTutor()
    payload = {"summary": "A useful explanation", "differences": ["A grammar contrast"]}
    tutor._client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: SimpleNamespace(text=json.dumps(payload))))
    monkeypatch.setattr(GeminiLinguisticTutor, "is_available", property(lambda self: True))
    assert tutor.explain("source", "bengali", "target", "hindi")["differences"] == payload["differences"]


def test_cross_script_inference_does_not_replace_names_and_serializes_processor(monkeypatch):
    import sys
    import time
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import nullcontext
    class Encoding(dict):
        def to(self, device): return self
    class Tokenizer:
        def __call__(self, *args, **kwargs): return Encoding(input_ids=[1])
        def batch_decode(self, *args, **kwargs): return ["আমি জল চাই।"]
    class Model:
        def parameters(self): yield SimpleNamespace(device="cpu")
        def generate(self, **kwargs): return [1]
    class Processor:
        active = 0
        def preprocess_batch(self, texts, src_lang, tgt_lang):
            assert (src_lang, tgt_lang) == ("hin_Deva", "ben_Beng")
            assert self.active == 0, "Two requests shared processor state"
            self.active += 1
            time.sleep(0.02)
            return texts
        def postprocess_batch(self, texts, lang):
            assert self.active == 1
            self.active -= 1
            return texts
    adapter = IndicTrans2Adapter()
    adapter.model, adapter.tokenizer, adapter.processor = Model(), Tokenizer(), Processor()
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(no_grad=nullcontext))
    monkeypatch.setattr(adapter, "_lazy_load_model", lambda: True)
    def shield(*args, **kwargs): raise AssertionError("Devanagari name anchors used for Bengali")
    monkeypatch.setattr(adapter, "_shield_proper_names", shield)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda text: adapter.translate(text, "hindi", "bengali"), ["कमल यहाँ है।", "आनंद वहाँ है।"]))
    assert all(result["engine"] == "indictrans2-320m-neural" for result in results)
    assert adapter.processor.active == 0


@pytest.mark.parametrize("body", [
    {"source_text":"source", "target_text":"target", "source_language":"hindi", "target_language":"hindi"},
    {"source_text":"আমি জল চাই।", "target_text":"मुझे पानी चाहिए।", "source_language":"hindi", "target_language":"marathi"},
    {"source_text":" ", "target_text":"target"},
])
def test_explain_rejects_invalid_pair_and_text(client, body):
    assert client.post("/api/explain", json=body).status_code == 422
