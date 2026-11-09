"""Freeze a document-disjoint NTREX evaluation and benchmark-excluded training data."""
import argparse
import hashlib
import json
import random
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from app.services.translation.corpus import normalize_source

NTREX_REVISION = '468c6b69c7f6a75d31d4743d9daba2af566cc18d'
LANGUAGES = ('bengali', 'hindi', 'marathi', 'english')
OUT = ROOT/'data/processed/translation-quality-v1'


def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows), encoding='utf-8')


def download():
    raw = ROOT/'data/raw/translation-quality-v1'
    raw.mkdir(parents=True, exist_ok=True)
    paths = {f'{language}.txt':f'NTREX-128/newstest2019-ref.{code}.txt'
             for language,code in [('bengali','ben'),('hindi','hin'),('marathi','mar')]}
    paths.update({'english.txt':'NTREX-128/newstest2019-src.eng.txt',
                  'documents.tsv':'DOCUMENT_IDS.tsv', 'LICENSE.md':'LICENSE.md'})
    for name, remote in paths.items():
        path = raw/name
        if path.exists() and path.stat().st_size: continue
        for attempt in range(3):
            try:
                url = f'https://raw.githubusercontent.com/MicrosoftTranslator/NTREX/{NTREX_REVISION}/{remote}'
                with urllib.request.urlopen(url, timeout=25) as response:
                    data = response.read(3_000_001)
                if not data or len(data)>3_000_000: raise ValueError('Unexpected file size')
                path.write_bytes(data)
                print('Downloaded', name, flush=True)
                break
            except OSError:
                if attempt==2: raise
                time.sleep(1)


def keys(rows):
    return {(language, normalize_source(text)) for row in rows for language,text in row['sentences'].items()}


def build():
    if (OUT/'manifest.json').exists():
        raise ValueError('Frozen split already exists; audit it instead of silently resampling')
    raw = ROOT/'data/raw/translation-quality-v1'
    columns = {language:(raw/f'{language}.txt').read_text(encoding='utf-8-sig').splitlines() for language in LANGUAGES}
    documents = (raw/'documents.tsv').read_text(encoding='utf-8-sig').splitlines()
    if len(set(map(len, columns.values())))!=1: raise ValueError('NTREX alignment mismatch')
    # DOCUMENT_IDS.tsv is aligned one document ID per sentence (possibly TSV fields).
    if len(documents)!=len(columns['english']): raise ValueError('Document alignment mismatch')
    teaching = read(ROOT/'data/processed/expanded/translation/teaching.jsonl')
    benchmark = read(ROOT/'data/processed/expanded/translation/test.jsonl')
    legacy = read(ROOT/'data/processed/translation/test.jsonl')
    blocked = keys(teaching+benchmark)
    blocked.update((language,normalize_source(row[language])) for row in legacy for language in ('hindi','marathi'))
    groups = defaultdict(list)
    for index,doc in enumerate(documents):
        sentences = {language:text[index].strip() for language,text in columns.items()}
        if any(not text for text in sentences.values()): continue
        if any((language,normalize_source(text)) in blocked for language,text in sentences.items()): continue
        groups[doc].append({'id':f'ntrex2019-{index+1}', 'document_id':doc, 'sentences':sentences,
                            'source':'NTREX-128', 'revision':NTREX_REVISION, 'license':'CC-BY-SA-4.0'})
    order = sorted(groups, key=lambda doc:hashlib.sha256(('bhashabridge-quality-v1:'+doc).encode()).hexdigest())
    validation, test = [], []
    for doc in order:
        if len(validation)<64: validation.extend(groups[doc])
        elif len(test)<128: test.extend(groups[doc])
        else: break
    if len(validation)<64 or len(test)<128: raise ValueError('Insufficient independent documents')
    write(OUT/'validation.jsonl', validation)
    write(OUT/'test.jsonl', test)
    # All NTREX sentences, including unused documents, are evaluation-only.
    protected = keys(benchmark+validation+test)
    train = []
    for row in teaching:
        if any((language,normalize_source(text)) in protected for language,text in row['sentences'].items()): continue
        train.append({'id':row['id'], 'source_language':'bengali', 'target_language':'marathi',
                      'source_text':row['sentences']['bengali'], 'target_text':row['sentences']['marathi'],
                      'source':'FLORES-200 dev', 'license':'CC-BY-SA-4.0', 'review_status':'external_reference'})
    correction_path = ROOT/'data/curated/translation_corrections_v1.jsonl'
    corrections = read(correction_path) if correction_path.exists() else []
    for row in corrections:
        if any((row[f'{side}_language'],normalize_source(row[f'{side}_text'])) in protected for side in ('source','target')):
            raise ValueError('Correction overlaps held-out data: '+row['id'])
    train.extend(corrections)
    write(OUT/'train.jsonl', train)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'LICENSE-NTREX.md').write_bytes((raw/'LICENSE.md').read_bytes())
    manifest = {'version':1, 'seed_policy':'SHA256(document ID + fixed version salt); whole documents',
                'validation_multiway_rows':len(validation), 'test_multiway_rows':len(test),
                'training_pairs':len(train), 'correction_pairs':len(corrections),
                'ntrex_revision':NTREX_REVISION,
                'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.jsonl'))},
                'raw_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.iterdir()) if p.is_file()},
                'sources':[{'name':'NTREX-128', 'url':'https://github.com/MicrosoftTranslator/NTREX',
                            'citation':'Federmann, Kocmi and Xin (2022), NTREX-128; and Barrault et al. (2019), WMT19.',
                            'license':'CC-BY-SA-4.0'}, {'name':'FLORES-200 dev','url':'https://github.com/facebookresearch/flores','license':'CC-BY-SA-4.0'}],
                'limitations':['News-domain subset, not the full NTREX corpus.',
                               'Upstream pretrained-model exposure is unknown.',
                               'Locally authored corrections are drafts, not native-speaker reviewed.',
                               'No NTREX or FLORES devtest reference is used for training.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(audit(),indent=2))


def audit():
    manifest=json.loads((OUT/'manifest.json').read_text())
    for name,digest in manifest['sha256'].items():
        if hashlib.sha256((OUT/name).read_bytes()).hexdigest()!=digest: raise ValueError('Frozen file changed: '+name)
    validation,test,train=(read(OUT/f'{name}.jsonl') for name in ('validation','test','train'))
    if {r['document_id'] for r in validation}&{r['document_id'] for r in test}: raise ValueError('Document leakage')
    if keys(validation)&keys(test): raise ValueError('Validation/test sentence overlap')
    forbidden=keys(validation+test+read(ROOT/'data/processed/expanded/translation/test.jsonl'))
    legacy=read(ROOT/'data/processed/translation/test.jsonl')
    forbidden.update((language,normalize_source(row[language])) for row in legacy for language in ('hindi','marathi'))
    correction_path=ROOT/'data/curated/translation_corrections_v1.jsonl'
    corrections=read(correction_path) if correction_path.exists() else []
    for row in train+corrections:
        if any((row[f'{side}_language'],normalize_source(row[f'{side}_text'])) in forbidden for side in ('source','target')):
            raise ValueError('Training leakage: '+row['id'])
    return {'training_pairs':len(train),'correction_pairs':len(corrections),'combined_training_pairs':len(train)+len(corrections),
            'validation_multiway_rows':len(validation),'test_multiway_rows':len(test),
            'training_overlap':0,'document_overlap':0,'hashes_verified':len(manifest['sha256'])}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    if args.audit: print(json.dumps(audit(),indent=2))
    else:
        if args.download: download()
        build()
