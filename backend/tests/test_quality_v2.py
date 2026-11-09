import importlib.util
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import prepare_translation_quality_v2 as data
from review_translation_quality import validate_batch
from curate_translation_corrections import approved_rows
from curate_translation_corrections import export as export_corrections
from judge_translation_candidates import validate_judgments
from run_translation_quality_v2 import passes
from translation_training_artifacts import save_epoch


def tsv(path,code,rows):
    path.write_text('src_lang\ttgt_lang\tsrc\ttgt\n'+''.join(f'eng_Latn\t{code}\t{en}\t{text}\n' for en,text in rows),encoding='utf-8')


def test_alignment_uses_shared_english_not_row_order(tmp_path):
    tsv(tmp_path/'daily-ben_Beng.tsv','ben_Beng',[('The door is open.','দরজাটি খোলা আছে।'),('The bus is here.','বাসটি এখানে আছে।')])
    tsv(tmp_path/'daily-mar_Deva.tsv','mar_Deva',[('The bus is here.','बस येथे आहे.'),('The door is open.','दार उघडे आहे.')])
    rows,_=data.join_subset('daily',tmp_path)
    paired={row['source_text']:row['target_text'] for row in rows}
    assert paired['দরজাটি খোলা আছে।']=='दार उघडे आहे.'
    assert paired['বাসটি এখানে আছে।']=='बस येथे आहे.'


def test_ambiguous_english_alignment_is_dropped(tmp_path):
    tsv(tmp_path/'daily-ben_Beng.tsv','ben_Beng',[('The door is open.','দরজাটি খোলা আছে।'),('The door is open.','দরজা খোলা।')])
    tsv(tmp_path/'daily-mar_Deva.tsv','mar_Deva',[('The door is open.','दार उघडे आहे.')])
    rows,stats=data.join_subset('daily',tmp_path)
    assert not rows and stats['ambiguous_bengali']==1


def test_v2_frozen_corpus_is_disjoint_and_excludes_drafts():
    result=data.audit()
    assert result['counts']['train']==6997
    assert result['cross_split_overlap']==result['old_test_overlap']==result['news_document_overlap']==0
    assert all(row['review_status']!='author_draft_not_native_reviewed' for row in data.read(data.OUT/'train.jsonl'))


def test_ai_review_ids_and_extra_direction_are_verified():
    row={'id':'bengali-marathi:4','verdict':'uncertain','categories':[],'severity':0,'confidence':'low','rationale':'Needs context.'}
    assert validate_batch([row],[row['id']])[row['id']]['verdict']=='uncertain'
    assert validate_batch({'reviews':[{**row,'direction':'bengali-marathi'}]},[row['id']])
    for bad in ([row,row],[{**row,'id':'unknown'}],[{**row,'direction':'hindi-marathi'}]):
        with pytest.raises(ValueError): validate_batch(bad,[row['id']])


def test_review_import_requires_explicit_human_attestation(tmp_path):
    with pytest.raises(ValueError,match='attestation'): approved_rows(tmp_path/'missing.csv')


def test_model_promotion_requires_both_domains_and_no_added_failures():
    baseline={'bleu':20.,'chrf_plus_plus':40.,'inference_failures':0}
    better={'bleu':21.,'chrf_plus_plus':41.,'inference_failures':0}
    assert passes(better,baseline,baseline,baseline)
    assert not passes({**better,'inference_failures':1},baseline,baseline,baseline)
    assert not passes(better,{**baseline,'chrf_plus_plus':39.},baseline,baseline)
    assert not passes({**better,'chrf_plus_plus':40.2},baseline,baseline,baseline)


def test_relative_cli_output_saves_checkpoint_and_portable_metadata(tmp_path,monkeypatch):
    class Model:
        def save_pretrained(self,path,**kwargs):
            path.mkdir(parents=True); (path/'adapter_model.safetensors').write_bytes(b'weights')
    monkeypatch.chdir(tmp_path)
    name=save_epoch(Model(),Path('experiments/run'),1,tmp_path)
    assert name=='experiments/run/epoch-1'
    assert (tmp_path/name/'adapter_model.safetensors').read_bytes()==b'weights'


def test_training_output_escape_is_rejected_before_writing(tmp_path):
    class Model:
        def save_pretrained(self,*args,**kwargs): pytest.fail('Attempted an outside write')
    with pytest.raises(ValueError): save_epoch(Model(),tmp_path.parent/'outside',1,tmp_path)


def test_model_judgments_cannot_approve_unknown_or_duplicate_cases():
    row={'id':'case-1','winner':'tie','major_error_a':False,'major_error_b':False,'rationale':'Equivalent wording.'}
    assert validate_judgments([row],['case-1'])
    for value in ([row,row],[{**row,'id':'other'}]):
        with pytest.raises(ValueError): validate_judgments(value,['case-1'])


def test_review_export_does_not_overwrite_human_edits(tmp_path):
    path=tmp_path/'review.csv'; export_corrections(path)
    original=path.read_bytes()
    with pytest.raises(ValueError,match='overwrite'): export_corrections(path)
    assert path.read_bytes()==original
