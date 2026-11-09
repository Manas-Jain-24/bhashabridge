import json
import pytest
from datetime import timedelta
from app.services.activity import now_utc
from app.models.entities import ArcadeReview, ArcadeSession
from app.services.gamification import arcade


def private(db,run):
    db.expire_all()
    return json.loads(db.get(ArcadeSession,run['session_id']).state_json)['questions'][run['answered']]


def answer(client,run,q,correct=True):
    choice=q['answer'] if correct else next(o['id'] for o in q['options'] if o['id']!=q['answer'])
    response=client.post('/api/arcade/answer',json={'session_id':run['session_id'],'question_id':q['id'],'choice_id':choice})
    assert response.status_code==200,response.text
    return response.json()


def test_beginner_topics_and_native_words(client):
    for language in ('hindi','marathi','bengali'):
        stats=client.get('/api/arcade/stats/'+language).json()
        assert stats['available_by_difficulty']['beginner']['recognize']==36
        assert stats['topic_counts']['numbers']==6
        run=client.post('/api/arcade/start',json={'language':language,'mode':'meaning','difficulty':'beginner','topic':'numbers'}).json()
        assert run['total']==6
        assert run['question']['prompt'] in ['one','two','three','four','five','six']
        assert run['question']['source'].endswith('editorial draft')


def test_mistake_is_due_and_correct_review_reschedules(client,db_session):
    run=client.post('/api/arcade/start',json={'language':'bengali','mode':'recognize','difficulty':'beginner','practice':'new'}).json()
    q=private(db_session,run)
    answer(client,run,q,False)
    stats=client.get('/api/arcade/stats/bengali').json()
    assert stats['review_due']['beginner']['recognize']==1
    review=client.post('/api/arcade/start',json={'language':'bengali','mode':'recognize','difficulty':'beginner','practice':'review'}).json()
    assert review['question']['id']==q['id'] and review['total']==1
    result=answer(client,review,q)
    assert result['done']
    db_session.expire_all()
    record=db_session.query(ArcadeReview).one()
    assert record.correct_streak==1 and record.mistakes==1 and record.due_at>now_utc()+timedelta(hours=23)
    assert client.get('/api/arcade/stats/bengali').json()['review_due']['beginner']['recognize']==0
    assert client.get('/api/arcade/stats/hindi').json()['review_due']['beginner']['recognize']==0


def test_review_plan_does_not_leak_answers_or_cross_difficulties(client,db_session):
    run=client.post('/api/arcade/start',json={'language':'bengali','mode':'recognize','difficulty':'advanced'}).json()
    q=private(db_session,run); answer(client,run,q,False)
    assert client.post('/api/arcade/start',json={'language':'bengali','mode':'recognize','difficulty':'beginner','practice':'review'}).status_code==409
    review=client.post('/api/arcade/start',json={'language':'bengali','mode':'recognize','difficulty':'advanced','practice':'review'}).json()
    assert not {'answer','reference','record','roman'} & set(review['question'])


def test_lesson_completion_and_bonus_are_persistent_and_replay_safe(client,db_session):
    request={'language':'bengali','mode':'meaning','lesson_id':'greetings'}
    bonuses=[]
    for _ in range(2):
        run=client.post('/api/arcade/start',json=request).json()
        assert run['total']==4 and run['difficulty']=='beginner'
        for i in range(4):
            q=private(db_session,run); run=answer(client,run,q)
        bonuses.append(run['feedback']['completion_xp'])
        retried=answer(client,run,q)
        assert retried['feedback']['completion_xp']==0 and retried['feedback']['xp_awarded']==0
    assert bonuses==[10,0]
    stats=client.get('/api/arcade/stats/bengali').json()
    assert stats['completed_lessons']==['greetings'] and stats['xp']==30


def test_incomplete_or_failed_lesson_does_not_complete_checkpoint(client,db_session):
    run=client.post('/api/arcade/start',json={'language':'bengali','mode':'meaning','lesson_id':'greetings'}).json()
    for _ in range(3):
        q=private(db_session,run); run=answer(client,run,q,False)
    assert run['done'] and not run['feedback']['lesson_completed']
    assert client.get('/api/arcade/stats/bengali').json()['completed_lessons']==[]


def test_content_has_honest_review_status_and_no_memory_promotion(client):
    course=client.get('/api/arcade/lessons/bengali').json()
    assert len(course['units'])==6 and sum(len(u['items']) for u in course['units'])==24
    assert course['units'][0]['review_status']=='source_checked'
    assert all(u['review_status']=='editorial_draft' for u in course['units'][1:])
    assert client.get('/api/arcade/lessons/hindi').json()['units']==[]
    assert client.post('/api/arcade/start',json={'language':'bengali','mode':'spell','lesson_id':'greetings'}).status_code==422
    assert client.post('/api/arcade/start',json={'language':'bengali','mode':'meaning','lesson_id':'missing'}).status_code==404
    assert client.post('/api/arcade/start',json={'language':'bengali','mode':'meaning','difficulty':'expert'}).status_code==422


def test_streamed_safetensors_loading_preserves_values(tmp_path):
    torch=pytest.importorskip('torch')
    save_file=pytest.importorskip('safetensors.torch').save_file
    from app.services.translation.low_memory import read_state
    path=tmp_path/'tiny.safetensors'
    original={'weight':torch.arange(16,dtype=torch.float32).reshape(4,4),'count':torch.tensor([3],dtype=torch.int64)}
    save_file(original,str(path))
    loaded=read_state(path,torch.float16)
    assert loaded['weight'].dtype==torch.float16 and torch.equal(loaded['weight'],original['weight'].half())
    assert loaded['count'].dtype==torch.int64 and loaded['count'].item()==3


def test_packed_encoder_is_independent_of_batch_padding():
    torch=pytest.importorskip('torch')
    from ml.transliteration.model import Encoder
    torch.manual_seed(7)
    enc=Encoder(20,8,12,12,dropout=0,packed=True).eval()
    single=torch.tensor([[1,4,2]])
    batch=torch.tensor([[1,4,2,0,0],[1,5,7,8,2]])
    with torch.inference_mode():
        a,ha=enc(single); b,hb=enc(batch)
    assert torch.allclose(ha[0],hb[0],atol=1e-6)
    assert torch.allclose(a[0],b[0,:3],atol=1e-6)


def test_promoted_bengali_artifacts_match_validation_hashes():
    import hashlib
    from pathlib import Path
    base=Path(__file__).resolve().parents[2]/'ml/models/bengali-v1'
    approval=json.loads((base/'promotion.json').read_text(encoding='utf-8'))
    assert approval['selection_split']=='validation' and approval['status']=='experimental'
    for file,key in [('inference.pt','weights_sha256'),('vocab.json','vocab_sha256')]:
        assert hashlib.sha256((base/file).read_bytes()).hexdigest()==approval[key]
    assert approval['validation_neural']['character_error_rate']<approval['validation_baseline']['character_error_rate']


def test_bengali_neural_dependencies_stay_lazy_in_test_mode(monkeypatch):
    from app.services.transliteration import bengali_neural
    def forbidden(): raise AssertionError('Test/mock mode loaded neural artifacts')
    monkeypatch.setattr(bengali_neural,'_load',forbidden)
    bengali_neural.predict_word.cache_clear()
    assert bengali_neural.predict_word('unseenword') is None
