"""Fresh evaluation documents and benchmark references must remain out of training."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('quality_data',ROOT/'scripts/prepare_translation_quality.py')
quality=importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


def test_frozen_quality_corpus_and_corrections_have_no_leakage():
    result=quality.audit()
    assert result['training_overlap']==result['document_overlap']==0
    assert result['hashes_verified']==3
    assert result['correction_pairs']==94
    assert result['combined_training_pairs']==1091


def test_audit_rejects_a_correction_copied_from_fresh_test(tmp_path,monkeypatch):
    # Use the actual frozen split but redirect only the optional correction path.
    original_read=quality.read
    test=original_read(quality.OUT/'test.jsonl')[0]
    leaked={'id':'leaked','source_language':'bengali','target_language':'marathi',
            'source_text':test['sentences']['bengali'],'target_text':test['sentences']['marathi']}
    def read(path):
        return [leaked] if path.name=='translation_corrections_v1.jsonl' else original_read(path)
    monkeypatch.setattr(quality,'read',read)
    with pytest.raises(ValueError,match='Training leakage'): quality.audit()


def test_authored_corrections_are_explicitly_unreviewed():
    rows=quality.read(ROOT/'data/curated/translation_corrections_v1.jsonl')
    assert all(row['review_status']=='author_draft_not_native_reviewed' for row in rows)
    assert len({r['id'] for r in rows})==len(rows)
