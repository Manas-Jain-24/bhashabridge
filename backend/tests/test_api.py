import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_language_and_script_detection():
    # Latin Marathi
    res = client.post("/api/analyze", json={
        "text": "mala udya college la jaycha aahe",
        "source_language": "auto",
        "target_language": "hindi",
        "preferred_script": "both"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["detected_language"] == "marathi"
    assert data["detected_script"] == "latin"
    assert "कॉलेजला" in data["native_text"] or "उद्या" in data["native_text"]
    assert len(data["vocabulary"]) > 0

def test_hindi_to_marathi_transliteration_and_translation():
    # User example: "Mujhe Marathi seekhni hai"
    res = client.post("/api/analyze", json={
        "text": "Mujhe Marathi seekhni hai",
        "source_language": "hindi",
        "target_language": "marathi",
        "preferred_script": "both"
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["translation_native"]) > 0
    assert len(data["translation_roman"]) > 0
    assert len(data["grammar_explanation"]) > 0

def test_indictrans2_adapter_and_translate_endpoint():
    res = client.post("/api/translate", json={
        "text": "मुझे कल कॉलेज जाना है।",
        "source_language": "hindi",
        "target_language": "marathi",
        "script": "both"
    })
    assert res.status_code == 200
    data = res.json()
    assert ("मला" in data["translation_native"] or "मी" in data["translation_native"])
    assert data["target_language"] == "marathi"

def test_explain_endpoint_m4_deep_linguistic():
    # Test arbitrary sentence triggering M4 dynamic alignment and contrast rules
    res = client.post("/api/explain", json={
        "source_text": "मुझे कल पानी चाहिए।",
        "source_language": "hindi",
        "target_text": "मला उद्या पाणी पाहिजे।",
        "target_language": "marathi"
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["word_explanations"]) > 0
    # Verify construction vs direct distinction
    has_construction = any(w["is_construction_based"] for w in data["word_explanations"])
    assert has_construction is True
    # Verify contrastive grammar points
    assert len(data["grammar_points"]) > 0
    # Verify learner traps
    assert len(data["common_mistakes"]) > 0

def test_transliterate_endpoints():
    # Latin to Devanagari
    res_dev = client.post("/api/transliterate", json={
        "text": "Mala Marathi shikaychi aahe",
        "language": "marathi",
        "direction": "latin_to_devanagari"
    })
    assert res_dev.status_code == 200
    assert "मला" in res_dev.json()["output"]

    # Devanagari to Latin
    res_lat = client.post("/api/transliterate", json={
        "text": "मला मराठी शिकायची आहे।",
        "language": "marathi",
        "direction": "devanagari_to_latin"
    })
    assert res_lat.status_code == 200
    assert "Mala" in res_lat.json()["output"]

def test_practice_generate_and_evaluate():
    gen_res = client.post("/api/practice/generate", json={
        "language": "marathi",
        "difficulty": "level_1"
    })
    assert gen_res.status_code == 200
    q = gen_res.json()
    assert "id" in q

    eval_res = client.post("/api/practice/evaluate", json={
        "question_id": "q1",
        "user_answer": "Mala udya college-la jaycha aahe.",
        "user_script": "roman"
    })
    assert eval_res.status_code == 200
    assert eval_res.json()["correctness"] is True

def test_progress_endpoint():
    res = client.get("/api/progress")
    assert res.status_code == 200
    data = res.json()
    # Verify strict separation of skills
    assert len(data["language_skills"]) > 0
    assert len(data["script_skills"]) > 0
    assert data["current_milestone"]["total_exercises"] > 0
    assert data["review_due_count"] > 0

def test_practice_attempt_persistence_and_history():
    # Submit a practice evaluation
    eval_res = client.post("/api/practice/evaluate", json={
        "question_id": "q1",
        "user_answer": "Mala udya college-la jaycha aahe.",
        "user_script": "roman"
    })
    assert eval_res.status_code == 200

    # Query history
    hist_res = client.get("/api/practice/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) > 0
    assert any("college-la" in h["user_answer"] for h in history)

def test_vocabulary_srs_review_queue():
    res = client.get("/api/vocabulary/review")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_milestones_roadmap_endpoint():
    res = client.get("/api/progress/milestones")
    assert res.status_code == 200
    roadmap = res.json()
    assert len(roadmap) >= 5
    # Verify levels 0 to 5 exist and have required fields
    levels = [item["level_number"] for item in roadmap]
    assert 0 in levels and 1 in levels and 2 in levels
    for item in roadmap:
        assert "title" in item
        assert "total_exercises" in item
        assert "progress_percentage" in item
        assert item["status"] in ["completed", "in_progress", "locked"]

def test_script_recommendation_and_bridge_mode_update():
    # Test recommendation endpoint
    rec_res = client.get("/api/progress/recommendation")
    assert rec_res.status_code == 200
    rec = rec_res.json()
    assert "current_mode" in rec
    assert "recommended_mode" in rec
    assert "composite_script_score" in rec
    assert "action_label" in rec

    # Test updating bridge mode
    update_res = client.post("/api/progress/bridge-mode", json={"mode": "advanced"})
    assert update_res.status_code == 200
    assert update_res.json()["updated_mode"] == "advanced"

    # Reset back to intermediate
    reset_res = client.post("/api/progress/bridge-mode", json={"mode": "intermediate"})
    assert reset_res.status_code == 200
    assert reset_res.json()["updated_mode"] == "intermediate"

def test_neural_transliteration_m7():
    import sys
    from pathlib import Path
    ml_dir = Path(__file__).resolve().parent.parent.parent / "ml"
    if str(ml_dir.parent) not in sys.path:
        sys.path.append(str(ml_dir.parent))
    from ml.transliteration.predictor import neural_transliterator

    assert neural_transliterator.is_loaded is True
    # Test word transliteration
    word_out = neural_transliterator.transliterate_word("aaj")
    assert len(word_out) > 0
    assert word_out == "आज"
    # Test sentence transliteration
    sent_out = neural_transliterator.transliterate_sentence("aaj ghar")
    assert "आज" in sent_out

def test_gamification_hub_endpoints():
    # 1. Profile endpoint
    prof_res = client.get("/api/gamification/profile")
    assert prof_res.status_code == 200
    prof = prof_res.json()
    assert "xp" in prof
    assert "streak_days" in prof
    assert "hearts" in prof
    assert "rank_title" in prof

    # 2. Skill Tree roadmap
    tree_res = client.get("/api/gamification/skill-tree")
    assert tree_res.status_code == 200
    nodes = tree_res.json()
    assert len(nodes) == 6
    assert nodes[0]["stars"] == 3

    # 3. Scramble questions with distractors
    scramble_res = client.get("/api/gamification/scramble")
    assert scramble_res.status_code == 200
    scrambles = scramble_res.json()
    assert len(scrambles) >= 5
    first_scramble = scrambles[0]
    assert any(t["is_distractor"] for t in first_scramble["tiles"])

    # 4. Blitz questions
    blitz_res = client.get("/api/gamification/blitz")
    assert blitz_res.status_code == 200
    blitz = blitz_res.json()
    assert len(blitz) >= 10

    # 5. Street Scenarios
    scenarios_res = client.get("/api/gamification/scenarios")
    assert scenarios_res.status_code == 200
    scenarios = scenarios_res.json()
    assert len(scenarios) == 3
    assert any(s["id"] == "fc_road_auto" for s in scenarios)

    # 6. Action recording (XP gain)
    action_res = client.post("/api/gamification/action", json={
        "action_type": "xp_gain",
        "xp_amount": 50
    })
    assert action_res.status_code == 200
    updated_prof = action_res.json()
    assert updated_prof["xp"] >= prof["xp"] + 50

def test_vocabulary_box_statistics_and_daily_quest():
    # 1. Leitner 5-box distribution statistics
    boxes_res = client.get("/api/vocabulary/boxes")
    assert boxes_res.status_code == 200
    b_data = boxes_res.json()
    assert "boxes" in b_data
    assert "total_words" in b_data
    assert b_data["total_words"] > 0
    assert "box_1" in b_data["boxes"]
    assert "retention_rate" in b_data

    # 2. Daily Quest Spotlight (Word of the day, Idiom of the day, Missions)
    quest_res = client.get("/api/vocabulary/daily-quest")
    assert quest_res.status_code == 200
    q_data = quest_res.json()
    assert "word_of_the_day" in q_data
    assert "idiom_of_the_day" in q_data
    assert "daily_missions" in q_data
    assert len(q_data["daily_missions"]) == 3
    assert q_data["word_of_the_day"]["marathi"] == "कडक"

def test_vocabulary_srs_rating_update():
    # Fetch review queue to get an active word id
    queue_res = client.get("/api/vocabulary/review?limit=5")
    assert queue_res.status_code == 200
    items = queue_res.json()
    assert len(items) > 0
    word_id = items[0]["id"]

    # Record "good" rating review
    review_res = client.post(f"/api/vocabulary/review/{word_id}", json={
        "rating": "good"
    })
    assert review_res.status_code == 200
    r_data = review_res.json()
    assert r_data["status"] == "success"
    assert "new_box" in r_data
    assert r_data["new_box"] >= 2

def test_pronunciation_evaluation():
    # 1. Near-perfect pronunciation
    high_res = client.post("/api/pronunciation/evaluate", json={
        "spoken_text": "Mala udya college la jaycha aahe",
        "target_phrase": "Mala udya college-la jaycha aahe"
    })
    assert high_res.status_code == 200
    h_data = high_res.json()
    assert h_data["accuracy_score"] >= 80.0
    assert h_data["is_native_pass"] is True
    assert len(h_data["phonetic_stress_guide"]) > 0

    # 2. Low accuracy pronunciation with missing words
    low_res = client.post("/api/pronunciation/evaluate", json={
        "spoken_text": "mujhe jaana",
        "target_phrase": "Mala udya college-la jaycha aahe"
    })
    assert low_res.status_code == 200
    l_data = low_res.json()
    assert l_data["accuracy_score"] < 50.0
    assert l_data["is_native_pass"] is False
    assert len(l_data["missing_words"]) > 0



