"""Freeze authored draft intents into six directional evaluation slices, never gold."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'data/quality/evaluation-draft-v1'


def build(directory=DIRECTORY):
    catalog=directory/'intents.tsv'
    with catalog.open(encoding='utf-8',newline='') as stream:
        intents=list(csv.DictReader(stream,delimiter='|'))
    if len(intents)!=50:
        raise ValueError(f'Expected 50 distinct draft intents, got {len(intents)}')
    rows=[]
    for index,intent in enumerate(intents,1):
        for source,target in itertools.permutations(('hindi','marathi','bengali'),2):
            rows.append({'id':f'intent-{index:03d}-{source}-{target}', 'intent_id':f'intent-{index:03d}',
                'group_id':intent['family'], 'split':'development' if intent['family'] in ('greeting','shopping') else 'test',
                'source_language':source,'target_language':target,'native_source':intent[source],
                'roman_source':intent[source+'_roman'], 'draft_target':intent[target],
                'draft_roman':intent[target+'_roman'], 'draft_english_intent':intent['english_intent'],
                'category':intent['category'],'ambiguity_expected':intent['category']=='ambiguity',
                'review_status':'draft','reviewer':None,'review_date':None,'acceptable_references':[],
                'provenance':'AI-authored diagnostic draft, November 2026; not human reviewed',
                'license':'CC0-1.0','purpose':'evaluation_only'})
    content=''.join(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n' for row in rows)
    manifest={'version':1,'frozen':True,'human_reviewed':False,'intents':50,'directional_rows':300,
              'native_and_roman_requests':600,'development_rows':sum(r['split']=='development' for r in rows),
              'test_rows':sum(r['split']=='test' for r in rows),
              'catalog_sha256':hashlib.sha256(catalog.read_bytes()).hexdigest(),
              'cases_sha256':hashlib.sha256(content.encode()).hexdigest(),
              'split_unit':'semantic family, shared across all directions and spellings',
              'note':'Frozen drafts support structural diagnostics, not accuracy or model promotion.'}
    output=directory/'cases.jsonl'
    if output.exists() or (directory/'manifest.json').exists():
        raise ValueError('Frozen evaluation already exists; create a new version rather than overwrite it')
    output.write_text(content,encoding='utf-8',newline='\n')
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__=='__main__':
    print(json.dumps(build(),indent=2))
