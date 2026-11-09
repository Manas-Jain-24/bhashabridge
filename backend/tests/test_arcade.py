import json
from datetime import timedelta
import pytest
from app.models.entities import ArcadeSession, UserGamification
from app.services.activity import now_utc
from app.services.gamification import arcade


def private_question(db, run):
    row = db.get(ArcadeSession, run["session_id"])
    return json.loads(row.state_json)["questions"][run["answered"]]


def correct_payload(question):
    if "answer" in question: return {"choice_id":question["answer"]}
    used=[]
    for letter in question["roman"]:
        used.append(next(i for i,c in enumerate(question["tiles"]) if c==letter and i not in used))
    return {"tile_ids":used}


@pytest.mark.parametrize("language", ["bengali", "hindi", "marathi"])
@pytest.mark.parametrize("mode", ["recognize", "spell", "meaning", "sprint"])
def test_game_start_is_language_scoped_and_hides_keys(client, language, mode):
    result = client.post("/api/arcade/start", json={"language":language,"mode":mode})
    assert result.status_code == 200
    data = result.json()
    assert data["language"] == language and data["mode"] == mode
    assert data["total"] == (60 if mode=="sprint" else 10)
    question = data["question"]
    assert not {"answer","expected","expected_spellings","reference","roman","record"} & set(question)
    if mode=="spell": assert 3 <= len(question["tiles"]) <= 18
    else: assert len({o["text"] for o in question["options"]}) == 4


def test_server_grades_and_retry_cannot_award_twice(client, db_session):
    run = client.post("/api/arcade/start", json={"language":"bengali","mode":"recognize"}).json()
    question=private_question(db_session,run)
    payload={"session_id":run["session_id"],"question_id":question["id"],**correct_payload(question)}
    first=client.post("/api/arcade/answer",json=payload).json()
    second=client.post("/api/arcade/answer",json=payload).json()
    assert first["feedback"]["correct"] and first["feedback"]["xp_awarded"]==5
    assert second["feedback"]["xp_awarded"]==0 and second["answered"]==1
    stats=client.get("/api/arcade/stats/bengali").json()
    assert stats["xp"]==5 and stats["best_score"]==100
    assert client.get("/api/arcade/stats/hindi").json()["xp"]==0


def test_daily_reward_survives_new_session(client, db_session, monkeypatch):
    fixed=arcade.make_questions("bengali","recognize",10)
    monkeypatch.setattr(arcade,"make_questions",lambda *args,**kwargs:json.loads(json.dumps(fixed)))
    rewards=[]
    for _ in range(2):
        run=client.post("/api/arcade/start",json={"language":"bengali","mode":"recognize"}).json()
        q=fixed[0]
        response=client.post("/api/arcade/answer",json={"session_id":run["session_id"],"question_id":q["id"],**correct_payload(q)})
        assert response.status_code==200
        rewards.append(response.json()["feedback"]["xp_awarded"])
    assert rewards==[5,0]


def test_spelling_requires_every_tile_once(client, db_session):
    run=client.post("/api/arcade/start",json={"language":"bengali","mode":"spell"}).json()
    q=private_question(db_session,run)
    base={"session_id":run["session_id"],"question_id":q["id"]}
    invalid=client.post("/api/arcade/answer",json={**base,"tile_ids":[0]*len(q["tiles"])})
    assert invalid.status_code==422
    valid=client.post("/api/arcade/answer",json={**base,**correct_payload(q)})
    assert valid.json()["feedback"]["correct"]


def test_wrong_answers_end_round_and_cannot_claim_xp(client, db_session):
    run=client.post("/api/arcade/start",json={"language":"marathi","mode":"recognize"}).json()
    for _ in range(3):
        db_session.expire_all()
        q=private_question(db_session,run)
        wrong=next(o["id"] for o in q["options"] if o["id"]!=q["answer"])
        run=client.post("/api/arcade/answer",json={"session_id":run["session_id"],"question_id":q["id"],"choice_id":wrong}).json()
        assert run["feedback"]["xp_awarded"]==0
    assert run["done"] and run["lives"]==0 and run["score"]==0
    assert client.get("/api/arcade/stats/marathi").json()["xp"]==0


def test_sprint_deadline_is_enforced_by_server(client, db_session):
    run=client.post("/api/arcade/start",json={"language":"bengali","mode":"sprint"}).json()
    q=private_question(db_session,run)
    session=db_session.get(ArcadeSession,run["session_id"])
    session.expires_at=now_utc()-timedelta(seconds=1); db_session.commit()
    result=client.post("/api/arcade/answer",json={"session_id":run["session_id"],"question_id":q["id"],**correct_payload(q)})
    assert result.status_code==409
    assert client.get("/api/arcade/session/"+run["session_id"]).json()["done"]


def test_forged_question_and_language_rejected(client):
    assert client.post("/api/arcade/start",json={"language":"unknown","mode":"recognize"}).status_code==422
    run=client.post("/api/arcade/start",json={"language":"hindi","mode":"recognize"}).json()
    assert client.post("/api/arcade/answer",json={"session_id":run["session_id"],"question_id":"fake","choice_id":"0"}).status_code==409
    assert client.get("/api/arcade/session/missing").status_code==404


def test_expanded_dataset_integrity():
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
    from check_expanded_data import audit
    report=audit()
    assert report["transliteration_train_pairs"]>221040
    assert report["translation_teaching_rows"]>=900
    assert report["translation_source_overlap"]==0


def test_training_loader_filters_new_native_script_data(tmp_path):
    pytest.importorskip("torch")
    from ml.transliteration.dataset import TransliterationDataset
    path=tmp_path/"training.jsonl"
    rows=[{"roman":"ami","native":"আমি","language":"bengali"},{"roman":"main","devanagari":"मैं","language":"hi"}]
    path.write_text("\n".join(json.dumps(r,ensure_ascii=False) for r in rows),encoding="utf-8")
    bengali=TransliterationDataset(str(path),build_vocab=True,language="bengali")
    assert len(bengali)==1 and bengali.pairs[0][1]=="আমি"
