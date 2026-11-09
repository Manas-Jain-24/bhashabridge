"""Regression coverage for multilingual routing and script isolation."""
import pytest
from app.core.languages import LANGUAGES, has_native
from app.models.entities import ReviewedTranslation
from app.services.translation.corpus import normalize_source
from app.services.translation.memory import lookup_reviewed
from app.services.translation.indictrans2 import IndicTrans2Adapter
from app.services.language_detection.detector import language_detector
from app.services.transliteration.service import transliteration_service
from app.services.explanation.engine import explanation_engine


def test_bengali_detection_and_experimental_roman_bridge():
    assert language_detector.detect_script("আমি বাংলা শিখতে চাই।") == "bengali"
    assert language_detector.detect_language("আপনি কেমন আছেন?") == "bengali"
    result = transliteration_service.transliterate("ami bangla shikhte chai!", "bengali", "latin_to_native")
    assert result == "আমি বাংলা শিখতে চাই!"
    assert transliteration_service.transliterate("আমি বাংলা", "bengali", "native_to_latin") == "ami bangla"
    assert has_native(result, "bengali") and not has_native(result, "hindi")


def test_bengali_memory_uses_actual_source_and_target_scripts(db_session):
    db_session.add(ReviewedTranslation(source_language="bengali", target_language="hindi",
        source_key=normalize_source("ধন্যবাদ"), source_text="ধন্যবাদ", target_text="धन्यवाद",
        target_roman="dhanyavaad", provenance="test_fixture"))
    db_session.flush()
    result = lookup_reviewed(db_session, "ধন্যবাদ!", "bengali", "hindi", "native")
    assert result["translation"] == "धन्यवाद"
    assert lookup_reviewed(db_session, "ধন্যবাদ", "bengali", "marathi") is None


def test_bengali_never_receives_marathi_rule_fallback():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        IndicTrans2Adapter().translate("আমি বাংলা শিখতে চাই।", "bengali", "hindi")
    assert exc.value.status_code == 503


def test_bengali_explanations_do_not_reuse_marathi_lessons(monkeypatch):
    from app.services.explanation.llm_tutor import llm_tutor
    monkeypatch.setattr(llm_tutor, "explain", lambda *args, **kwargs: None)
    result = explanation_engine.explain("আমি জল চাই।", "bengali", "मुझे पानी चाहिए।", "hindi")
    assert result["explanation_source"] == "unavailable"
    assert result["examples"] == [] and result["grammar_points"] == []


def test_language_api_and_validation(client):
    assert client.get("/api/languages").json()["bengali"]["flores"] == "ben_Beng"
    for source, target in [("bengali", "bengali"), ("unknown", "hindi")]:
        assert client.post("/api/translate", json={"text": "hello", "source_language": source, "target_language": target}).status_code == 422
    result = client.post("/api/translate", json={"text": "আমি জল চাই।", "source_language": "bengali", "target_language": "hindi"})
    assert result.status_code == 503


def test_analyze_preserves_bengali_and_explicit_target(client, monkeypatch):
    from app.api.routes import analyze
    def translate(db, text, source_language, target_language, script, **context):
        assert text == "আমি জল চাই।" and source_language == "bengali" and target_language == "marathi"
        return {"translation": "मला पाणी पाहिजे।", "translation_native": "मला पाणी पाहिजे।", "translation_roman": "mala paani pahije", "english_meaning": "", "model_source": "test_model"}
    monkeypatch.setattr(analyze, "translate_with_memory", translate)
    result = client.post("/api/analyze", json={"text": "আমি জল চাই।", "source_language": "auto", "target_language": "marathi"})
    assert result.status_code == 200
    data = result.json()
    assert data["target_language"] == "marathi" and data["detected_language"] == "bengali"
    assert data["native_text"] == "আমি জল চাই।"
    assert data["explanation_source"] == "unavailable"


def test_processor_handles_cross_script_round_trip():
    pytest.importorskip("indicnlp")
    from app.services.translation.indic_processor import IndicScriptProcessor
    processor = IndicScriptProcessor()
    prepared = processor.preprocess_batch(["আমি বাংলা শিখতে চাই।"], "ben_Beng", "hin_Deva")
    assert prepared[0].startswith("ben_Beng hin_Deva ")
    assert not has_native(prepared[0], "bengali")
    restored = processor.postprocess_batch([prepared[0].split(" ", 2)[2]], "ben_Beng")[0]
    assert has_native(restored, "bengali")
