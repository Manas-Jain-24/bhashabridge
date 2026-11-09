"""Versioned, language-neutral content loading and explicit editorial provenance."""
import json
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[4]


@lru_cache(maxsize=1)
def vocabulary():
    return json.loads((ROOT/'data/lessons/starter_vocabulary.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=3)
def course(language):
    path = ROOT/f'data/lessons/{language}_starter.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
        'language':language, 'title':'Starter vocabulary', 'units':[], 'review_note':vocabulary()['note']}


def starter_rows(language, mode, topic='all'):
    return [{'native':w[language][0], 'roman':w[language][1],
             'prompt':w['english'] if mode=='meaning' else w[language][1],
             'english':w['english'], 'topic':w['topic'], 'aliases':[w[language][1]],
             'source':'BhashaBridge starter vocabulary · editorial draft'}
            for w in vocabulary()['words'] if language in w and (topic=='all' or w['topic']==topic)]


def lesson_rows(language, lesson_id):
    units=course(language)['units']
    selected=next((u for u in units if u['id']==lesson_id),None)
    if selected is None: raise HTTPException(404,'Lesson not found')
    def convert(unit, item):
        return {**item,'prompt':item['english'], 'source':f"BhashaBridge Foundations · {unit['review_status']}"}
    return [convert(selected,i) for i in selected['items']], [convert(u,i) for u in units for i in u['items']]
