"""Corpus-powered games with private answer keys and replay-safe rewards."""
import hashlib
import json
import math
import random
import uuid
from collections import Counter
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.models.entities import ArcadeSession, ArcadeReview, LearningActivity
from app.services.gamification.curriculum import starter_rows, lesson_rows, course
from app.services.activity import record_activity, now_utc
from app.services.translation.corpus import normalize_source

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "data/processed/expanded"
MODES = ("recognize", "spell", "meaning", "sprint")
RNG = random.SystemRandom()


def read_rows(path):
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@lru_cache(maxsize=80)
def bank(language, mode, difficulty='advanced', topic='all'):
    if mode in ("spell", "sprint"):
        return bank(language, "recognize", difficulty, topic)
    if difficulty == 'beginner':
        return starter_rows(language, mode, topic)
    if difficulty == 'intermediate':
        return [r for r in bank(language,mode,'advanced') if (len(r['native'].split())<=14 if mode=='meaning' else len(r['native'])<=8 and len(r['roman'])<=12)]
    if mode == "meaning":
        entries = [{"native": r["sentences"][language], "prompt": r["sentences"]["english"], "roman": "", "source": "FLORES-200 dev"}
                   for r in read_rows(DATA / "translation/teaching.jsonl")
                   if language in r["sentences"] and 2 <= len(r["sentences"][language].split()) <= 22]
    else:
        entries = [{**r, "prompt": r["roman"]} for r in read_rows(DATA / "lexicon.jsonl")
                   if r["language"] == language and 2 <= len(r["native"]) <= 16 and 3 <= len(r["roman"]) <= 18 and r["attestations"] >= 2]
    # Do not create questions whose prompt has conflicting corpus answers.
    answers = {}
    for row in entries:
        answers.setdefault(normalize_source(row["prompt"]), set()).add(normalize_source(row["native"]))
    entries = [r for r in entries if len(answers[normalize_source(r["prompt"])]) == 1]
    entries = list({(normalize_source(r["native"]), normalize_source(r["prompt"])): r for r in entries}.values())
    return entries


def make_questions(language, mode, limit=10, difficulty='advanced', topic='all', entries=None, distractors=None):
    rows = entries if entries is not None else bank(language, mode, difficulty, topic)
    if len(rows) < 4:
        raise HTTPException(503, "Game data is unavailable. Run scripts/expand_datasets.py first.")
    questions = []
    for row in RNG.sample(rows, min(limit, len(rows))):
        record = hashlib.sha256((language + ":" + row["native"] + ":" + row["prompt"]).encode()).hexdigest()[:24]
        question = {"id": record, "reference": row["native"], "roman": row["roman"], "source": row["source"], "record": record, 'difficulty':difficulty}
        if mode == "spell":
            tiles = list(row["roman"])
            RNG.shuffle(tiles)
            question.update(prompt=row["native"], tiles=tiles, expected_spellings=row.get("aliases", [row["roman"]]))
        else:
            candidates = [r for r in (distractors if distractors is not None else rows) if normalize_source(r["native"]) != normalize_source(row["native"]) and row["prompt"] not in r.get("aliases", [])]
            alternatives = list({normalize_source(r["native"]): r["native"] for r in candidates}.values())
            if len(alternatives) < 3: continue
            choices = [row["native"]] + RNG.sample(alternatives, 3)
            RNG.shuffle(choices)
            options = [{"id": str(i), "text": text} for i, text in enumerate(choices)]
            question.update(prompt=row["prompt"], options=options, answer=str(choices.index(row["native"])))
        questions.append(question)
    return questions


def public_question(question, mode):
    # Explicit allow-list: expected spelling and answer IDs are never sent early.
    return {key: question[key] for key in ("id", "prompt", "options", "tiles", "source") if key in question}


def session_view(session, state):
    remaining = max(0, math.ceil((session.expires_at - now_utc()).total_seconds()))
    done = session.completed_at is not None or remaining == 0
    index = session.answer_count
    return {"session_id": session.id, "language": session.language, "mode": session.mode,
            "score": session.score, "correct": session.correct_count, "answered": index,
            "total": len(state["questions"]), "lives": max(0, 3 - (index - session.correct_count)),
            "remaining_seconds": remaining, "done": done,
            'difficulty':state.get('difficulty','advanced'), 'practice':state.get('practice','mixed'), 'lesson_id':state.get('lesson_id'),
            "question": None if done or index >= len(state["questions"]) else public_question(state["questions"][index], session.mode)}


def due_reviews(db, language, mode, difficulty, user_id=1):
    rows = db.query(ArcadeReview).filter_by(user_id=user_id, language=language, mode=mode).filter(ArcadeReview.due_at<=now_utc()).order_by(ArcadeReview.due_at,ArcadeReview.id).all()
    return [json.loads(r.question_json) for r in rows if json.loads(r.question_json).get('difficulty','advanced')==difficulty]


def start_session(db, language, mode, difficulty='advanced', topic='all', practice='mixed', lesson_id=None, user_id=1):
    limit = 60 if mode == 'sprint' else 10
    if lesson_id:
        if mode!='meaning': raise HTTPException(422,'Lesson practice uses sentence matching')
        entries, distractors = lesson_rows(language,lesson_id)
        questions = make_questions(language,mode,len(entries),difficulty='beginner',entries=entries,distractors=distractors)
        difficulty='beginner'
    else:
        due = due_reviews(db,language,mode,difficulty,user_id=user_id) if practice!='new' else []
        if practice=='review':
            questions=due[:limit]
            if not questions: raise HTTPException(409,'Nothing is due in this language, mode and difficulty. Try a new round.')
        else:
            questions = make_questions(language, mode, limit, difficulty=difficulty, topic=topic)
            # Revisit up to half a round, while retaining new practice.
            selected=due[:limit//2]
            known={q['record'] for q in selected}
            questions=(selected+[q for q in questions if q['record'] not in known])[:limit]
    if not questions: raise HTTPException(503, "No unambiguous questions are available.")
    now = now_utc()
    session = ArcadeSession(id=str(uuid.uuid4()), user_id=user_id, language=language, mode=mode,
        state_json=json.dumps({"questions": questions, "last": None, 'difficulty':difficulty,'practice':practice,'lesson_id':lesson_id}, ensure_ascii=False),
        score=0, correct_count=0, answer_count=0, started_at=now,
        expires_at=now + timedelta(seconds=60 if mode == "sprint" else 900))
    db.add(session); db.commit()
    return session_view(session, json.loads(session.state_json))


def update_review(db, session, question, correct):
    user_id = session.user_id
    review=db.query(ArcadeReview).filter_by(user_id=user_id,language=session.language,mode=session.mode,record=question['record']).first()
    now=now_utc()
    if review is None:
        review=ArcadeReview(user_id=user_id,language=session.language,mode=session.mode,record=question['record'],
            question_json=json.dumps(question,ensure_ascii=False),correct_streak=0,mistakes=0,due_at=now,updated_at=now)
        db.add(review)
    if correct:
        review.correct_streak+=1
        review.due_at=now+timedelta(days=[1,3,7,14,30][min(review.correct_streak-1,4)])
    else:
        review.correct_streak=0; review.mistakes+=1; review.due_at=now
    review.updated_at=now


def get_session(db, session_id, user_id=1):
    session = db.query(ArcadeSession).filter_by(id=session_id, user_id=user_id).with_for_update().first()
    if session is None: raise HTTPException(404, "Game session not found.")
    return session


def submit_answer(db, request, user_id=1):
    session = get_session(db, request.session_id, user_id=user_id)
    state = json.loads(session.state_json)
    last = state.get("last")
    if last and last["question_id"] == request.question_id:
        # A network retry returns the prior result, without a second reward.
        return {**session_view(session, state), "feedback": {**last, "xp_awarded": 0, 'completion_xp':0}}
    view = session_view(session, state)
    if view["done"]: raise HTTPException(409, "This session is finished or expired. Start a new game.")
    question = state["questions"][session.answer_count]
    if request.question_id != question["id"]: raise HTTPException(409, "This is not the current question.")
    if session.mode == "spell":
        indexes = request.tile_ids
        if indexes is None or request.choice_id is not None or len(indexes) != len(question["tiles"]) or set(indexes) != set(range(len(question["tiles"]))):
            raise HTTPException(422, "Use each spelling tile exactly once.")
        correct = "".join(question["tiles"][i] for i in indexes) in question["expected_spellings"]
    else:
        if request.tile_ids is not None or request.choice_id not in {o["id"] for o in question["options"]}:
            raise HTTPException(422, "Select one of this question's answers.")
        correct = request.choice_id == question["answer"]
    xp = 0
    try:
        update_review(db,session,question,correct)
        if correct:
            key = f"arcade:{session.language}:{session.mode}:{question['record']}:{now_utc().date()}"
            if record_activity(db, key, "arcade_" + session.language, xp=5, user_id=user_id): xp = 5
            session.correct_count += 1
            session.score += 100
        session.answer_count += 1
        if session.answer_count >= len(state["questions"]) or session.answer_count - session.correct_count >= 3:
            session.completed_at = now_utc()
        lesson_complete = bool(state.get('lesson_id') and session.answer_count==len(state['questions']) and session.correct_count>=math.ceil(len(state['questions'])*.8))
        completion_xp=0
        if lesson_complete and record_activity(db,f"lesson_complete:{session.language}:{state['lesson_id']}",f'lesson_complete_{session.language}',xp=10,user_id=user_id):
            completion_xp=10
        state["last"] = {"question_id": question["id"], "correct": correct,
                          "reference": question["reference"], "roman": question["roman"], "xp_awarded": xp,
                          'lesson_completed':lesson_complete,'completion_xp':completion_xp}
        session.state_json = json.dumps(state, ensure_ascii=False)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An answer was already saved. Reload your session.")
    return {**session_view(session, state), "feedback": state["last"]}


def stats(db, language, user_id=1):
    events = db.query(LearningActivity).filter_by(user_id=user_id, kind="arcade_" + language).all()
    xp = sum(e.xp_awarded for e in events)
    best = db.query(func.max(ArcadeSession.score)).filter_by(user_id=user_id, language=language).scalar() or 0
    reviews=db.query(ArcadeReview).filter_by(user_id=user_id,language=language).all()
    due={level:{mode:0 for mode in MODES} for level in ('beginner','intermediate','advanced')}
    for review in reviews:
        level=json.loads(review.question_json).get('difficulty','advanced')
        if review.due_at<=now_utc() and level in due and review.mode in due[level]: due[level][review.mode]+=1
    completions=db.query(LearningActivity).filter_by(user_id=user_id,kind=f'lesson_complete_{language}').all()
    completed=[e.event_key.split(':',2)[2] for e in completions]
    xp+=sum(e.xp_awarded for e in completions)
    return {"language": language, "xp": xp, "level": 1 + xp // 100,
            "next_level_xp": (1 + xp // 100) * 100, "correct_first_awards": len(events),
            "best_score": best, "badges": [name for threshold, name in [(10, "Script Explorer"), (50, "Word Collector"), (200, "Language Adventurer")] if len(events) >= threshold],
            "available": {mode: len(bank(language, mode)) for mode in MODES},
            'available_by_difficulty':{level:{mode:len(bank(language,mode,level)) for mode in MODES} for level in due},
            'review_due':due,'mastered_items':sum(r.correct_streak>=3 for r in reviews),'completed_lessons':completed,
            'topic_counts':dict(Counter(r['topic'] for r in starter_rows(language,'recognize')))}
