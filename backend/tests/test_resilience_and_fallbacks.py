"""
BhashaBridge — Resilience, Edge Case, and Fallback Test Suite
Validates:
- Health check endpoint completeness and absence of leaked secrets
- Input validation (empty text, invalid schema, long text)
- Transliteration edge cases (pure Devanagari, mixed Roman/Devanagari, Roman)
- Translation bidirectional flow (Hindi -> Marathi, Marathi -> Hindi)
- Proper name shielding without multi-name collisions
- Neural fallback behavior when models or GPUs are unavailable
- Database fallback resilience (SQLite fallback)
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.services.translation.indictrans2 import indictrans2_adapter
from app.services.transliteration.service import transliteration_service
from app.models.database import check_db_health, SessionLocal

def test_health_check_endpoint(client: TestClient):
    """Ensure /api/health returns 200 with engine statuses and no secret leakage."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert "models" in data
    assert "transliteration" in data["models"]
    assert "translation" in data["models"]
    assert "explanation_tutor" in data["models"]
    # Verify no tokens or keys are leaked in health check
    raw_str = str(data)
    assert "AIza" not in raw_str
    assert "hf_" not in raw_str
    assert "secret" not in raw_str.lower()

def test_translate_empty_payload(client: TestClient):
    """Validation: missing text should return 422 Unprocessable Entity."""
    resp = client.post("/api/translate", json={})
    assert resp.status_code == 422

def test_transliterate_empty_text(client: TestClient):
    """Validation: empty text should return 422."""
    resp = client.post("/api/transliterate", json={"text": "", "language": "hindi"})
    assert resp.status_code == 422

def test_analyze_empty_payload(client: TestClient):
    """Validation: empty analyze text should return 422."""
    resp = client.post("/api/analyze", json={"text": ""})
    assert resp.status_code == 422

def test_transliteration_preserves_pure_devanagari():
    """Ensure Devanagari input is preserved without double-conversion."""
    dev_text = "मला आज अभ्यास करायचा आहे"
    result = transliteration_service.transliterate(dev_text, language="marathi", direction="latin_to_devanagari")
    assert result == dev_text

def test_transliteration_roman_to_devanagari():
    """Ensure standard Roman input transliterates to Devanagari."""
    rom_text = "namaste"
    result = transliteration_service.transliterate(rom_text, language="hindi", direction="latin_to_devanagari")
    assert any('\u0900' <= c <= '\u097f' for c in result)

def test_transliteration_preserves_pure_roman_for_devanagari_to_latin():
    """Ensure Roman text is not corrupted when devanagari_to_latin is invoked on it."""
    rom_text = "Already English"
    result = transliteration_service.transliterate(rom_text, language="hindi", direction="devanagari_to_latin")
    assert result == rom_text

def test_translation_hindi_to_marathi(client: TestClient):
    """Test Hindi to Marathi translation with fallback flag."""
    resp = client.post("/api/translate", json={
        "text": "मुझे पानी चाहिए",
        "source_language": "hindi",
        "target_language": "marathi",
        "script": "both"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "मला" in data["translation_native"] or "पाणी" in data["translation_native"]
    assert data["model_source"] in ["indictrans2-320m-neural", "reviewed_database", "curated_corpus", "rule_fallback"]

def test_translation_marathi_to_hindi(client: TestClient):
    """Test Marathi to Hindi reverse translation."""
    resp = client.post("/api/translate", json={
        "text": "मला पाणी पाहिजे",
        "source_language": "marathi",
        "target_language": "hindi",
        "script": "both"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "पानी" in data["translation_native"] or "मुझे" in data["translation_native"]

def test_multi_name_shielding_no_collision():
    """
    Ensure sentences with multiple proper names (e.g. Kamal and Anand)
    shield each name with distinct anchors so they don't overwrite each other.
    """
    text = "कमल और आनंद दोस्त हैं"
    shielded, shield_map = indictrans2_adapter._shield_proper_names(text)
    # Check that both names are in the shield map under different anchors
    assert "कमल" in shield_map.values()
    assert "आनंद" in shield_map.values()
    # Check anchors are distinct
    anchors_used = list(shield_map.keys())
    assert len(anchors_used) == len(set(anchors_used))
    # Test unshielding restores both original names
    restored = indictrans2_adapter._unshield_proper_names(shielded, shield_map)
    assert "कमल" in restored
    assert "आनंद" in restored

def test_database_health_check():
    """Ensure database connection check reports connected."""
    db_info = check_db_health()
    assert isinstance(db_info, dict)
    assert db_info["status"] == "connected"

def test_practice_generate_and_evaluate(client: TestClient):
    """Test end-to-end practice question generation and answer evaluation."""
    gen_resp = client.post("/api/practice/generate", json={
        "language": "marathi",
        "difficulty": "level_1",
        "topic": "general"
    })
    assert gen_resp.status_code == 200
    q_data = gen_resp.json()
    assert "id" in q_data
    assert "prompt" in q_data

    eval_resp = client.post("/api/practice/evaluate", json={
        "question_id": q_data["id"],
        "user_answer": "test answer",
        "user_script": "roman"
    })
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert "correctness" in eval_data
    assert "score" in eval_data
    assert "explanation" in eval_data


def test_transliteration_model_lazy_loading():
    """Verify that constructing/importing transliteration service does NOT load neural weights."""
    from app.services.transliteration.service import NeuralTransliterationService
    svc = NeuralTransliterationService()
    assert svc._neural_model is None
    assert svc._is_loaded is False
    assert svc._load_attempts == 0
    assert svc._load_failed is False


def test_transliteration_lazy_load_guard_on_missing_weights(monkeypatch):
    """Verify that when weights/neural deps are unavailable, it attempts loading up to max_retries, sets _load_failed, and falls back to rule engine quickly without repeated attempts."""
    import builtins
    from app.core.config import settings
    monkeypatch.setattr(settings, "USE_MOCK_MODELS", False)
    monkeypatch.setattr(settings, "TESTING", False)
    from app.services.transliteration.service import NeuralTransliterationService
    svc = NeuralTransliterationService()

    real_import = builtins.__import__
    def fake_import(name, *args, **kwargs):
        if "ml.transliteration.predictor" in name:
            raise ImportError("Simulated missing PyTorch/weights")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # First request: triggers guarded load attempt and gracefully falls back
    res1 = svc.transliterate("namaste", language="hindi")
    assert res1 == "नमस्ते"
    assert svc._load_failed is True
    assert svc._load_attempts == svc._max_load_attempts

    # Second request: must NOT re-attempt loading; routes directly to rule fallback
    attempts_before = svc._load_attempts
    res2 = svc.transliterate("dost", language="hindi")
    assert res2 == "दोस्त"
    assert svc._load_attempts == attempts_before


def test_mixed_script_transliteration_hindi():
    """Verify token-by-token processing: Devanagari preserved, Latin transliterated, whitespace/punct preserved."""
    from app.services.transliteration.service import NeuralTransliterationService
    svc = NeuralTransliterationService()
    svc._load_failed = True  # force rule fallback (neural unavailable)

    text = "namaste भारत dost mitra!"
    result = svc.transliterate(text, language="hindi", direction="latin_to_devanagari")
    assert "भारत" in result
    assert "नमस्ते" in result
    assert result.endswith("!")
    assert result == "नमस्ते भारत दोस्त मित्र!"


def test_mixed_script_transliteration_marathi():
    """Verify Marathi mixed script with Roman and Devanagari tokens."""
    from app.services.transliteration.service import NeuralTransliterationService
    svc = NeuralTransliterationService()
    svc._load_failed = True  # force rule fallback

    text = "मी ghaari jaato आहे."
    result = svc.transliterate(text, language="marathi", direction="latin_to_devanagari")
    assert "मी" in result
    assert "आहे." in result
    # Latin tokens are transliterated
    assert any(c in result for c in ["घरी", "घारि"])


def test_mixed_script_preserves_whitespace_and_punctuation():
    """Whitespace, tabs, newlines, and punctuation must remain in exact positions."""
    from app.services.transliteration.service import NeuralTransliterationService
    svc = NeuralTransliterationService()
    svc._load_failed = True

    text = "   namaste,   भारत?   kya   haal   hai...   "
    result = svc.transliterate(text, language="hindi")
    assert result.startswith("   ")
    assert result.endswith("   ")
    assert ",   भारत?   " in result
    assert "..." in result


def test_db_isolation_does_not_modify_normal_bhashabridge_db(client: TestClient, verify_production_db_unmodified):
    """Verify that test client operations mutate only the isolated test db, leaving production bhashabridge.db SHA-256 and mtime completely unchanged."""
    import hashlib
    info = verify_production_db_unmodified
    prod_db = info["path"]

    # Verify state before endpoint calls
    if info["exists"]:
        curr_mtime = prod_db.stat().st_mtime
        curr_sha256 = hashlib.sha256(prod_db.read_bytes()).hexdigest()
        assert curr_mtime == info["mtime"], "Pre-call mtime mismatch on production bhashabridge.db"
        assert curr_sha256 == info["sha256"], "Pre-call SHA-256 mismatch on production bhashabridge.db"

    # Execute health check and practice flow that exercises the DB session
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["database"]["status"] == "connected"

    # Verify state after endpoint calls
    if info["exists"]:
        post_mtime = prod_db.stat().st_mtime
        post_sha256 = hashlib.sha256(prod_db.read_bytes()).hexdigest()
        assert post_mtime == info["mtime"], "Post-call mtime changed on production bhashabridge.db"
        assert post_sha256 == info["sha256"], "Post-call SHA-256 changed on production bhashabridge.db"


def test_production_database_import_without_testing_flag(monkeypatch):
    """
    Regression test for P0: Verify database module can be imported and initialized
    in non-test production mode (TESTING=false) without NameError ('os' missing)
    or unexpected crash.
    """
    import os
    import importlib
    monkeypatch.setenv("TESTING", "false")
    from app.core.config import settings
    monkeypatch.setattr(settings, "TESTING", False)

    import app.models.database as db_mod
    importlib.reload(db_mod)

    assert hasattr(db_mod, "engine")
    assert db_mod.engine is not None
    assert db_mod.active_db_type in ["sqlite", "postgresql", "sqlite_fallback"]
