"""Build conservative BPCC English-pivot pairs and new document-separated test data."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.services.translation.corpus import normalize_source

OUT=ROOT/'data/processed/translation-quality-v2'
RAW=ROOT/'data/raw/translation-quality-v2'
REVISION='5bde309374f21c39e7c3d505f28ae11f58f2a220'
NTREX_REVISION='468c6b69c7f6a75d31d4743d9daba2af566cc18d'


def read(path): return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='\n') as handle:
        for row in rows: handle.write(json.dumps(row,ensure_ascii=False)+'\n')


def canonical(value): return ' '.join(unicodedata.normalize('NFC',value).split())


def text_keys(rows):
    result=set()
    for row in rows:
        values=row.get('sentences') or {row['source_language']:row['source_text'],row['target_language']:row['target_text'],
                                      'english':row.get('english_text','')}
        result.update((language,normalize_source(text)) for language,text in values.items() if text)
    return result


def load_column(path,code):
    entries=defaultdict(set); rejected=0
    with path.open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle,delimiter='\t')
        if reader.fieldnames!=['src_lang','tgt_lang','src','tgt']: raise ValueError('Unexpected BPCC TSV schema')
        for row in reader:
            if row['src_lang']!='eng_Latn' or row['tgt_lang']!=code:
                rejected+=1; continue
            source,target=canonical(row['src']),canonical(row['tgt'])
            if not source or not target: rejected+=1; continue
            entries[source].add(target)
    conflicts={source for source,targets in entries.items() if len(targets)>1}
    return {source:next(iter(targets)) for source,targets in entries.items() if source not in conflicts},conflicts,rejected


def join_subset(subset,raw=RAW):
    bengali,bn_conflicts,bn_bad=load_column(raw/f'{subset}-ben_Beng.tsv','ben_Beng')
    marathi,mr_conflicts,mr_bad=load_column(raw/f'{subset}-mar_Deva.tsv','mar_Deva')
    rows=[]; rejected=0
    for english in sorted(set(bengali)&set(marathi)):
        source,target=bengali[english],marathi[english]
        def native_fraction(text,lo,hi):
            letters=[char for char in text if unicodedata.category(char).startswith('L')]
            return sum(lo<=ord(char)<=hi for char in letters)/max(len(letters),1)
        if not 3<=len(english)<=1000 or not 2<=len(source)<=1200 or not 2<=len(target)<=1200:
            rejected+=1; continue
        if native_fraction(source,0x0980,0x09ff)<0.5 or native_fraction(target,0x0900,0x097f)<0.5:
            rejected+=1; continue
        rows.append({'id':'bpcc-'+hashlib.sha256(english.encode()).hexdigest()[:20],
                     'source_language':'bengali','target_language':'marathi','source_text':source,'target_text':target,
                     'english_text':english,'subset':subset,'source':'AI4Bharat BPCC-H-'+subset.title(),
                     'source_revision':REVISION,'license':'CC-BY-4.0',
                     'alignment':'exact_shared_English_NFC_whitespace_only',
                     'review_status':'upstream_human_translations; direct_pair_not_locally_reviewed'})
    return rows,{'joined':len(rows),'rejected_quality':rejected,'ambiguous_bengali':len(bn_conflicts),
                 'ambiguous_marathi':len(mr_conflicts),'rejected_schema_rows':bn_bad+mr_bad}


def legacy_protected():
    rows=[]
    for path in (ROOT/'data/processed/expanded/translation/test.jsonl',
                 ROOT/'data/processed/translation-quality-v1/validation.jsonl',
                 ROOT/'data/processed/translation-quality-v1/test.jsonl'):
        rows.extend(read(path))
    protected=text_keys(rows)
    for row in read(ROOT/'data/processed/translation/test.jsonl'):
        protected.update((language,normalize_source(row[language])) for language in ('hindi','marathi'))
    return protected


def freeze_news():
    raw=ROOT/'data/raw/translation-quality-v1'
    columns={language:(raw/f'{language}.txt').read_text(encoding='utf-8-sig').splitlines()
             for language in ('bengali','marathi','english')}
    docs=(raw/'documents.tsv').read_text(encoding='utf-8-sig').splitlines()
    if len({len(docs),*map(len,columns.values())})!=1: raise ValueError('NTREX alignment mismatch')
    old=read(ROOT/'data/processed/translation-quality-v1/validation.jsonl')+read(ROOT/'data/processed/translation-quality-v1/test.jsonl')
    excluded_docs={row['document_id'] for row in old}
    forbidden=legacy_protected()|text_keys(read(ROOT/'data/processed/expanded/translation/teaching.jsonl'))
    groups=defaultdict(list)
    all_news=[]
    for i,doc in enumerate(docs):
        row={'id':f'ntrex2019-{i+1}','document_id':doc,'source_language':'bengali','target_language':'marathi',
             'source_text':columns['bengali'][i],'target_text':columns['marathi'][i],'english_text':columns['english'][i],
             'subset':'news','source':'NTREX-128','source_revision':NTREX_REVISION,'license':'CC-BY-SA-4.0',
             'review_status':'external_reference'}
        all_news.append(row)
        if doc not in excluded_docs and not text_keys([row])&forbidden: groups[doc].append(row)
    validation,test=[],[]
    for doc in sorted(groups,key=lambda value:hashlib.sha256(('quality-v2:'+value).encode()).hexdigest()):
        if len(validation)<64: validation.extend(groups[doc])
        elif len(test)<139: test.extend(groups[doc])
        else: break
    if len(validation)<64 or len(test)<139: raise ValueError('Not enough unused news documents')
    return validation,test,text_keys(all_news)


def download():
    from huggingface_hub import hf_hub_download,get_token
    from app.core.config import settings
    RAW.mkdir(parents=True,exist_ok=True)
    for subset in ('daily','wiki'):
        for code in ('ben_Beng','mar_Deva'):
            destination=RAW/f'{subset}-{code}.tsv'
            if destination.exists(): continue
            path=hf_hub_download('ai4bharat/BPCC',f'{subset}/{code}.tsv',repo_type='dataset',revision=REVISION,
                                 token=settings.HF_TOKEN or get_token())
            destination.write_bytes(Path(path).read_bytes())


def build(train_size=6000):
    if (OUT/'manifest.json').exists(): raise ValueError('Frozen v2 data exists; do not silently resample')
    news_validation,news_test,all_news=freeze_news()
    forbidden=legacy_protected()|all_news
    candidates={}; stats={}; conflicts=set()
    for subset in ('daily','wiki'):
        rows,stats[subset]=join_subset(subset)
        for row in rows:
            key=canonical(row['english_text'])
            if key in candidates:
                if (row['source_text'],row['target_text'])!=(candidates[key]['source_text'],candidates[key]['target_text']): conflicts.add(key)
                continue
            candidates[key]=row
    pools=defaultdict(list); exclusions=Counter(); seen=set()
    for english,row in candidates.items():
        if english in conflicts: exclusions['cross_subset_conflict']+=1; continue
        if text_keys([row])&forbidden: exclusions['existing_benchmark_or_news_overlap']+=1; continue
        pair=(normalize_source(row['source_text']),normalize_source(row['target_text']))
        if pair in seen: exclusions['duplicate_pair']+=1; continue
        seen.add(pair); pools[row['subset']].append(row)
    validation,test,train=[],[],[]
    heldout_keys=set()
    for subset in ('daily','wiki'):
        ordered=sorted(pools[subset],key=lambda row:hashlib.sha256(('bpcc-v2:'+row['english_text']).encode()).hexdigest())
        valid_subset=[]; test_subset=[]; remaining=[]
        for row in ordered:
            row_keys=text_keys([row])
            if row_keys&heldout_keys: exclusions['heldout_alias']+=1; continue
            if len(valid_subset)<80: valid_subset.append(row); heldout_keys.update(row_keys)
            elif len(test_subset)<80: test_subset.append(row); heldout_keys.update(row_keys)
            else: remaining.append(row)
        if min(len(valid_subset),len(test_subset))<80: raise ValueError('Insufficient held-out BPCC pairs')
        validation.extend(valid_subset); test.extend(test_subset)
        pools[subset]=remaining
    # Re-check earlier candidates against both subsets' final held-out keys.
    for subset,cap in (('daily',2000),('wiki',max(train_size-2000,0))):
        eligible=[row for row in pools[subset] if not text_keys([row])&heldout_keys]
        train.extend(eligible[:cap])
    if len(train)<train_size: raise ValueError(f'Only {len(train)} eligible pairs; refusing synthetic padding')
    # General reference replay, filtered against every evaluation split.
    replay=[]
    protected=forbidden|heldout_keys|text_keys(news_validation+news_test)
    for row in read(ROOT/'data/processed/expanded/translation/teaching.jsonl'):
        example={'id':row['id'],'source_language':'bengali','target_language':'marathi',
                 'source_text':row['sentences']['bengali'],'target_text':row['sentences']['marathi'],
                 'english_text':row['sentences']['english'],'subset':'general_replay','source':'FLORES-200 dev',
                 'license':'CC-BY-SA-4.0','review_status':'external_reference'}
        if not text_keys([example])&protected: replay.append(example)
    train.extend(replay)
    for split,rows in (('train',train),('validation',validation),('test',test),('validation_news',news_validation),('test_news',news_test)):
        write(OUT/f'{split}.jsonl',rows)
    manifest={'version':2,'bpcc_revision':REVISION,'ntrex_revision':NTREX_REVISION,
              'counts':{name:len(rows) for name,rows in [('train',train),('validation',validation),('test',test),('validation_news',news_validation),('test_news',news_test)]},
              'training_by_subset':dict(Counter(row['subset'] for row in train)),
              'import_statistics':stats,'excluded':dict(exclusions),
              'sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(OUT.glob('*.jsonl'))},
              'raw_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(RAW.glob('*.tsv'))},
              'provenance':{'BPCC':'https://huggingface.co/datasets/ai4bharat/BPCC','NTREX':'https://github.com/MicrosoftTranslator/NTREX'},
              'licenses':{'BPCC-H-Daily and BPCC-H-Wiki':'CC-BY-4.0','NTREX and FLORES-200':'CC-BY-SA-4.0'},
              'limitations':['English-pivot human translations are not direct Bengali–Marathi human review.',
                             'BPCC was used to pretrain IndicTrans2; BPCC holdouts measure local adaptation, not unseen pretraining data.',
                             'New NTREX documents were excluded from all local adaptation; upstream exposure is unknown.',
                             '94 unreviewed local drafts are excluded from v2 training.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps(audit(),indent=2))


def audit():
    manifest=json.loads((OUT/'manifest.json').read_text())
    for name,digest in manifest['sha256'].items():
        if hashlib.sha256((OUT/name).read_bytes()).hexdigest()!=digest: raise ValueError('Frozen data changed: '+name)
    splits={name:read(OUT/f'{name}.jsonl') for name in manifest['counts']}
    if any(len(rows)!=manifest['counts'][name] for name,rows in splits.items()): raise ValueError('Count mismatch')
    names=list(splits)
    for i,name in enumerate(names):
        for other in names[i+1:]:
            if text_keys(splits[name])&text_keys(splits[other]): raise ValueError(f'Split overlap: {name}/{other}')
    if text_keys(splits['train'])&legacy_protected(): raise ValueError('Legacy test contamination')
    v1=read(ROOT/'data/processed/translation-quality-v1/validation.jsonl')+read(ROOT/'data/processed/translation-quality-v1/test.jsonl')
    old_docs={row['document_id'] for row in v1}
    vdocs={r['document_id'] for r in splits['validation_news']}; tdocs={r['document_id'] for r in splits['test_news']}
    if vdocs&tdocs or (vdocs|tdocs)&old_docs: raise ValueError('News document overlap')
    return {'counts':manifest['counts'],'training_by_subset':manifest['training_by_subset'],
            'hashes_verified':len(manifest['sha256']),'cross_split_overlap':0,'old_test_overlap':0,'news_document_overlap':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true'); parser.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    if args.audit: print(json.dumps(audit(),indent=2))
    else:
        if args.download: download()
        build()
