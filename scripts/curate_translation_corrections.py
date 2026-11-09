"""Export draft corrections for review; import only explicitly attested human decisions."""
import argparse
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from prepare_translation_quality_v2 import OUT,legacy_protected,read,text_keys

DRAFTS=ROOT/'data/curated/translation_corrections_v1.jsonl'
FIELDS=['id','source_language','target_language','source_text','draft_target_text','decision',
        'corrected_target_text','reviewer_id','reviewed_at','notes']


def export(path):
    if path.exists(): raise ValueError('Review file exists; refusing to overwrite human work')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS); writer.writeheader()
        for row in read(DRAFTS):
            writer.writerow({**{key:row[key] for key in ('id','source_language','target_language','source_text')},
                             'draft_target_text':row['target_text'],'decision':'pending'})


def approved_rows(path,attested=False):
    if not attested: raise ValueError('Explicit human-review attestation is required')
    drafts={row['id']:row for row in read(DRAFTS)}
    protected=legacy_protected()
    for split in ('validation','test','validation_news','test_news'): protected|=text_keys(read(OUT/f'{split}.jsonl'))
    approved=[]; seen=set()
    with path.open(encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            if row['id'] in seen: raise ValueError('Duplicate correction ID')
            seen.add(row['id'])
            if row['id'] not in drafts: raise ValueError('Unknown/benchmark row cannot become a correction')
            original=drafts[row['id']]
            for key in ('source_language','target_language','source_text'):
                if row[key]!=original[key]: raise ValueError('Draft identity/source changed')
            if row['draft_target_text']!=original['target_text']: raise ValueError('Original draft changed; use corrected_target_text')
            if row['decision'] in ('pending','reject',''): continue
            if row['decision'] not in ('accept','revise'): raise ValueError('Unknown review decision')
            reviewer=row['reviewer_id'].strip()
            if len(reviewer)<3 or reviewer.lower() in ('ai','gemini','assistant','automated'):
                raise ValueError('A human reviewer identity is required')
            reviewed_at=date.fromisoformat(row['reviewed_at'])
            if reviewed_at>date.today(): raise ValueError('Future review date')
            target=original['target_text'] if row['decision']=='accept' else row['corrected_target_text'].strip()
            if not target: raise ValueError('Revised target is empty')
            item={**original,'target_text':target,'review_status':'human_attested',
                  'reviewer_id':reviewer,'reviewed_at':reviewed_at.isoformat(),'review_notes':row['notes'],
                  'original_draft_sha256':hashlib.sha256(json.dumps(original,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
            if text_keys([item])&protected: raise ValueError('Reviewed correction overlaps a frozen benchmark')
            approved.append(item)
    return approved


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['export','import'])
    parser.add_argument('--input',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--attest-human-review',action='store_true')
    args=parser.parse_args()
    if args.action=='export':
        export(args.output); print('Exported 94 pending draft corrections; no approvals recorded.')
    else:
        if not args.input: parser.error('--input is required')
        rows=approved_rows(args.input,args.attest_human_review)
        if not rows: raise ValueError('No human-approved rows; no training file written')
        if args.output.exists(): raise ValueError('Output exists; create a new version')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8',newline='\n')
        print(f'Wrote {len(rows)} human-attested corrections. No application database was modified.')


if __name__=='__main__': main()
