"""Benchmark summaries must distinguish full coverage from diagnostic subsets."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

import pytest
from app.core.languages import LANGUAGES

spec = importlib.util.spec_from_file_location(
    'translation_reports', Path(__file__).resolve().parents[2] / 'scripts/finalize_translation_reports.py')
reports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reports)


def fixture_reports(tmp_path, count):
    corpus = tmp_path / 'test.jsonl'
    rows = [{'sentences': {language: f'{language} sentence {i}.' for language in LANGUAGES}} for i in range(3)]
    corpus.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    directory = tmp_path / 'reports'
    directory.mkdir()
    for source, target in itertools.permutations(LANGUAGES, 2):
        report = {
            'identity': {'source_language': source, 'target_language': target,
                         'test_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
                         'model': 'test', 'model_revision': 'frozen', 'precision': 'float16',
                         'processor': 'test', 'generation': {}, 'requested_examples': count},
            'complete': True, 'examples': count,
            'predictions': [{'index': i, 'source': rows[i]['sentences'][source],
                             'reference': rows[i]['sentences'][target],
                             'prediction': rows[i]['sentences'][target]} for i in range(count)]}
        (directory / f'{source}-{target}.json').write_text(json.dumps(report), encoding='utf-8')
    return directory, corpus


@pytest.mark.parametrize('count,diagnostic', [(2, True), (3, False)])
def test_summary_labels_actual_split_coverage(tmp_path, count, diagnostic):
    directory, corpus = fixture_reports(tmp_path, count)
    summary = reports.finalize(directory, corpus)
    assert summary['complete']
    assert summary['diagnostic_subset'] is diagnostic
    assert summary['examples_per_direction'] == count
    assert summary['full_split_examples_per_direction'] == 3
    assert len(summary['directions']) == 6
    # A saved summary does not count as a seventh direction on a repeat run.
    assert reports.finalize(directory, corpus) == summary


@pytest.mark.parametrize('corruption', ['incomplete', 'duplicate_index', 'reference', 'checksum', 'precision'])
def test_summary_rejects_invalid_evidence_before_writing(tmp_path, corruption):
    directory, corpus = fixture_reports(tmp_path, 3)
    path = next(directory.glob('*.json'))
    report = json.loads(path.read_text())
    if corruption == 'incomplete': report['complete'] = False
    elif corruption == 'duplicate_index': report['predictions'][1]['index'] = 0
    elif corruption == 'reference': report['predictions'][0]['reference'] = 'wrong reference'
    elif corruption == 'checksum':
        corpus.write_text(corpus.read_text() + '\n', encoding='utf-8')
    else: report['identity']['precision'] = 'float32'
    path.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError): reports.finalize(directory, corpus)
    assert not (directory / 'summary.json').exists()
