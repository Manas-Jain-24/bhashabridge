"""Behavioral regressions from the October project review."""
from datetime import timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.database import Base
from app.models.entities import User, VocabularyWord, VocabularyReview, LearningActivity, Progress, Milestone, UserGamification
from app.services.activity import now_utc, current_streak
from app.services.vocabulary.srs_service import srs_service
from app.services.practice.engine import practice_service
from app.services.gamification.engine import gamification_service, SCRAMBLE_BANK, BLITZ_QUESTIONS, STREET_SCENARIOS
from app.schemas.gamification import GamificationActionRequest


@pytest.fixture
def small_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, username="test"))
        db.add(User(id=2, username="second"))
        db.add(VocabularyWord(id=1, language="marathi", devanagari="पाणी", roman="paani", english_meaning="water"))
        db.commit()
        yield db
    engine.dispose()


@pytest.mark.parametrize("q", [q for q in practice_service.QUESTIONS_BANK if q.get("options")], ids=lambda q: q["id"])
def test_correct_options_are_accepted(q):
    option = next(o for o in q["options"] if o["id"] == q["correct_option_id"])
    for field in ("text_roman", "text_devanagari"):
        assert practice_service.evaluate_answer(q["id"], option[field]).correctness
    assert practice_service.evaluate_answer(q["id"], option["text_roman"], selected_option_id=option["id"]).correctness
    wrong = next(o for o in q["options"] if o["id"] != option["id"])
    assert not practice_service.evaluate_answer(q["id"], wrong["text_roman"], selected_option_id=wrong["id"]).correctness


@pytest.mark.parametrize("spoken,target", [("कल", "काल"), ("पनि", "पानी"), ("मल", "मला")])
def test_vowel_marks_are_preserved(client, spoken, target):
    result = client.post("/api/pronunciation/evaluate", json={"spoken_text": spoken, "target_phrase": target})
    assert result.status_code == 200
    assert result.json()["accuracy_score"] < 100
    assert not result.json()["is_native_pass"]


def test_empty_speech_is_a_valid_zero_result(client):
    response = client.post("/api/pronunciation/evaluate", json={"spoken_text": "", "target_phrase": "मला पाणी पाहिजे"})
    assert response.status_code == 200
    assert response.json()["accuracy_score"] == 0
    assert response.json()["spoken_text"] == ""


def test_review_is_scheduled_and_returns_after_elapsed_time(small_db):
    now = now_utc()
    result = srs_service.record_review_result(small_db, 1, "good", now=now)
    assert result["next_review_days"] == 3
    assert srs_service.get_due_count(small_db, now=now) == 0
    assert srs_service.get_review_queue(small_db, now=now) == []
    assert srs_service.get_due_count(small_db, now=now + timedelta(days=3)) == 1
    assert srs_service.get_due_count(small_db, user_id=2, now=now) == 1
    small_db.expire_all()
    review = small_db.query(VocabularyReview).one()
    assert review.last_reviewed_at == now
    assert review.next_review_at == now + timedelta(days=3)
    # Shared vocabulary remains unchanged.
    assert small_db.get(VocabularyWord, 1).repetition_count == 0


def test_duplicate_review_does_not_reward_or_advance(small_db):
    srs_service.record_review_result(small_db, 1, "easy")
    xp = small_db.query(UserGamification).one().xp
    with pytest.raises(HTTPException) as error:
        srs_service.record_review_result(small_db, 1, "easy")
    assert error.value.status_code == 409
    assert small_db.query(UserGamification).one().xp == xp
    assert small_db.query(VocabularyReview).one().repetition_count == 1


def test_zero_hearts_and_streak_remain_zero(small_db):
    small_db.add(UserGamification(user_id=1, hearts=0, streak_days=0))
    small_db.commit()
    result = gamification_service.process_action(small_db, GamificationActionRequest(action_type="heart_lost"))
    assert result.hearts == 0
    assert result.streak_days == 0


def test_chest_is_once_per_day_and_does_not_create_streak(small_db):
    request = GamificationActionRequest(action_type="claim_chest", xp_amount=500)
    first = gamification_service.process_action(small_db, request)
    second = gamification_service.process_action(small_db, request)
    assert first.xp == second.xp == 30
    assert second.daily_chest_claimed
    assert second.streak_days == 0


def test_scramble_requires_answer_and_is_idempotent(small_db):
    question = SCRAMBLE_BANK[0]
    with pytest.raises(HTTPException):
        gamification_service.process_action(small_db, GamificationActionRequest(action_type="complete_scramble", exercise_id=question["id"]))
    request = GamificationActionRequest(action_type="complete_scramble", exercise_id=question["id"], answer_tokens=question["target_tokens"])
    first = gamification_service.process_action(small_db, request)
    second = gamification_service.process_action(small_db, request)
    assert first.xp == second.xp == 25
    assert second.completed_scrambles == 1
    assert second.streak_days == 1


def test_scenario_uses_real_choices_and_awards_badge_once(small_db):
    scenario = STREET_SCENARIOS[0]
    choices = [next(c for c in step["choices"] if c["is_best"]) for step in scenario["steps"]]
    request = GamificationActionRequest(action_type="complete_scenario", scenario_id=scenario["id"], choice_ids=[c["id"] for c in choices], xp_amount=500)
    first = gamification_service.process_action(small_db, request)
    second = gamification_service.process_action(small_db, request)
    assert first.xp == second.xp == sum(c["xp_reward"] for c in choices)
    assert second.completed_scenarios == [scenario["id"]]
    assert scenario["badge_id"] in second.unlocked_badges


def test_blitz_recomputes_score_and_rewards_only_improvement(small_db):
    question = BLITZ_QUESTIONS[0]
    payload = dict(action_type="blitz_score", score=100000, answers=[{"question_id": question["id"], "answer": question["is_true"]}])
    first = gamification_service.process_action(small_db, GamificationActionRequest(**payload))
    second = gamification_service.process_action(small_db, GamificationActionRequest(**payload))
    assert first.blitz_high_score == question["points"]
    assert first.xp == second.xp == question["points"] // 5


@pytest.mark.parametrize("payload", [{"action_type": "xp_gain", "xp_amount": 500}, {"action_type": "unlock_badge", "badge_id": "fake"}, {"action_type": "claim_chest", "xp_amount": -1}, {"action_type": "unknown"}])
def test_invalid_reward_requests_are_rejected(client, payload):
    assert client.post("/api/gamification/action", json=payload).status_code == 422


def test_every_roadmap_level_has_enough_distinct_questions():
    for level, topic, required in [(0,"greetings",10),(1,"requests",10),(2,"college",10),(3,"conversation",12),(4,"grammar",15),(5,"script",20)]:
        questions = [q for q in practice_service.QUESTIONS_BANK if q["difficulty"] == f"level_{level}" and q["topic"] == topic]
        assert len({q["expected_dev"] for q in questions}) >= required


def test_unrelated_and_repeated_questions_do_not_advance_milestones(client, db_session):
    progress = db_session.query(Progress).one()
    assert progress.completed_exercises == 0
    # College question cannot advance the greetings milestone.
    for _ in range(2):
        assert client.post("/api/practice/evaluate", json={"question_id":"q1", "user_answer":"Mala udya college-la jaycha aahe."}).status_code == 200
    db_session.expire_all()
    assert db_session.query(Progress).one().completed_exercises == 0
    q = next(q for q in practice_service.QUESTIONS_BANK if q["difficulty"] == "level_0" and q["topic"] == "greetings")
    for _ in range(2):
        client.post("/api/practice/evaluate", json={"question_id":q["id"], "user_answer":q["expected_rom"]})
    db_session.expire_all()
    assert db_session.query(Progress).one().completed_exercises == 1
    generated = client.post("/api/practice/generate", json={"difficulty": "level_0", "topic": "greetings"})
    assert generated.status_code == 200
    assert generated.json()["id"] != q["id"]


def test_final_milestone_finishes_and_count_is_capped(client, db_session):
    milestone = db_session.query(Milestone).order_by(Milestone.level.desc()).first()
    progress = db_session.query(Progress).one()
    progress.milestone_id = milestone.id
    progress.completed_exercises = milestone.total_exercises - 1
    db_session.commit()
    q = next(q for q in practice_service.QUESTIONS_BANK if q["topic"] == "script")
    response = client.post("/api/practice/evaluate", json={"question_id":q["id"], "user_answer":q["expected_dev"]})
    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.query(Progress).one().status == "completed"
    assert db_session.query(Progress).one().completed_exercises == milestone.total_exercises
    assert client.get("/api/progress/milestones").json()[-1]["status"] == "completed"


def test_script_exercise_does_not_accept_copying_roman_prompt():
    q = next(q for q in practice_service.QUESTIONS_BANK if q.get("required_script") == "devanagari")
    assert not practice_service.evaluate_answer(q["id"], q["expected_rom"]).correctness
    assert practice_service.evaluate_answer(q["id"], q["expected_dev"]).correctness


def test_daily_quests_reflect_saved_activity_and_streak_dates(small_db):
    now = now_utc()
    before = srs_service.get_daily_quest_data(small_db)["daily_missions"]
    assert all(m["current"] == 0 for m in before)
    srs_service.record_review_result(small_db, 1, "good", now=now)
    after = srs_service.get_daily_quest_data(small_db)["daily_missions"]
    assert after[0]["current"] == 1
    assert current_streak(small_db, now=now)[0] == 1
    assert current_streak(small_db, now=now + timedelta(days=1))[0] == 1
    assert current_streak(small_db, now=now + timedelta(days=2))[0] == 0


def test_runtime_and_training_corpora_exclude_heldout_sources():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from check_corpus_leakage import audit
    assert all(x["overlapping_sources"] == 0 for x in audit().values())


def test_fifth_review_awards_daily_mission_once(small_db):
    for word_id in range(2, 7):
        small_db.add(VocabularyWord(id=word_id, language="marathi", devanagari=f"शब्द{word_id}", roman=f"word{word_id}", english_meaning="test"))
    small_db.commit()
    for word_id in range(1, 7):
        srs_service.record_review_result(small_db, word_id, "good")
    assert small_db.query(UserGamification).one().xp == 6 * 15 + 30
    assert small_db.query(LearningActivity).filter_by(kind="mission").count() == 1
    assert srs_service.get_daily_quest_data(small_db)["daily_missions"][0]["completed"]


def test_speech_rewards_and_mission_are_not_replayed(client):
    phrase = "मला उद्या कॉलेजला जायचं आहे"
    failed = client.post("/api/pronunciation/evaluate", json={"spoken_text": "चूक", "target_phrase": phrase})
    assert failed.status_code == 200
    assert failed.json()["xp_awarded"] == 0
    first = client.post("/api/pronunciation/evaluate", json={"spoken_text": phrase, "target_phrase": phrase})
    second = client.post("/api/pronunciation/evaluate", json={"spoken_text": phrase, "target_phrase": phrase})
    assert first.json()["xp_awarded"] == 40
    assert second.json()["xp_awarded"] == 0
    assert client.get("/api/gamification/profile").json()["xp"] == 90


def test_new_tables_can_be_added_without_resetting_legacy_rows():
    from app.models.database import init_db
    from sqlalchemy import inspect
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    VocabularyWord.__table__.create(engine)
    with Session(engine) as db:
        db.add(User(id=1, username="existing"))
        db.add(VocabularyWord(id=1, devanagari="पाणी", roman="paani", english_meaning="water", box_level=4, repetition_count=12))
        db.commit()
    init_db(target_engine=engine, seed=False)
    assert {"learning_activities", "vocabulary_reviews"} <= set(inspect(engine).get_table_names())
    with Session(engine) as db:
        assert db.get(User, 1).username == "existing"
        assert db.get(VocabularyWord, 1).repetition_count == 12
        assert db.get(VocabularyWord, 1).box_level == 4
    engine.dispose()


@pytest.mark.parametrize("xp,level", [(0,1),(200,1),(201,2),(500,2),(501,3),(2001,5)])
def test_rank_boundaries_match_level(small_db, xp, level):
    small_db.add(UserGamification(user_id=1, xp=xp))
    small_db.commit()
    assert gamification_service.get_profile_dto(small_db).level == level
