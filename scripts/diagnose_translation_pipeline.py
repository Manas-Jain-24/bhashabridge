"""Paired runtime diagnostics: canonical native, Roman-local and Roman-hybrid.

The authored cases and English intents are unreviewed diagnostics, not an accuracy
benchmark or a promotion test. No outputs become training or reviewed-memory data.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def save(path, report):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT / 'data/quality/runtime-diagnostic-v1.jsonl')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--local-only', action='store_true')
    parser.add_argument('--pause', type=float, default=0, help='Seconds between cases to respect provider request limits')
    parser.add_argument('--retry-provider-once', action='store_true', help='Retain first failure, wait for the cooldown, then try once more')
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger('app.services.translation.contextual').setLevel(logging.INFO)
    if args.limit < 0 or args.pause < 0 or args.pause > 60:
        parser.error('Limit cannot be negative; pause must be between 0 and 60 seconds')
    import torch
    torch.set_num_threads(2)
    from app.core.config import settings
    from app.models.database import SessionLocal
    from app.services.translation.service import translate_with_memory
    from app.services.translation.contextual import PROMPT_VERSION, protected_values
    from app.services.translation.indictrans2 import indictrans2_adapter

    rows = [json.loads(line) for line in args.cases.read_text(encoding='utf-8').splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    if len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate diagnostic IDs')
    if args.output.exists():
        raise ValueError('Choose a new output file; diagnostics never overwrite previous runs')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        'complete': False, 'cases_sha256': hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        'prompt_version': PROMPT_VERSION, 'gemini_model': settings.GEMINI_TRANSLATION_MODEL,
        'model': settings.INDICTRANS2_MODEL_CHECKPOINT, 'expected_examples': len(rows),
        'request_pause_seconds': args.pause, 'retry_provider_once': args.retry_provider_once,
        'human_reviewed': False, 'scope': 'Authored diagnostic examples; not a general accuracy estimate.',
        'predictions': [],
    }
    for row in rows:
        comparison = {**row, 'paths': {}}
        for mode, source_text in [('canonical_local', row['native_source']), ('roman_local', row['input']),
                                  *([] if args.local_only else [('roman_hybrid', row['input'])])]:
            start = time.monotonic()
            try:
                with SessionLocal() as db:
                    result = translate_with_memory(db, source_text, row['source_language'], row['target_language'],
                                                   translation_mode='hybrid' if mode == 'roman_hybrid' else 'local')
                    first_attempt = None
                    if (mode == 'roman_hybrid' and args.retry_provider_once
                            and result.get('context_issue') in ('provider_error', 'cooldown')):
                        first_attempt = {key: value for key, value in result.items() if not key.startswith('_')}
                        print(f"Provider cooldown for {row['id']}; retaining first attempt and retrying once in 31 seconds", flush=True)
                        time.sleep(31)
                        result = translate_with_memory(db, source_text, row['source_language'], row['target_language'],
                                                       translation_mode='hybrid')
                comparison['paths'][mode] = {key: value for key, value in result.items() if key != '_explanation'}
                if first_attempt is not None:
                    comparison['paths'][mode]['first_attempt'] = first_attempt
                comparison['paths'][mode]['protected_values_preserved'] = (
                    protected_values(source_text) == protected_values(result['translation_native']))
            except Exception as exc:
                comparison['paths'][mode] = {'error': type(exc).__name__}
            comparison['paths'][mode]['elapsed_seconds'] = round(time.monotonic() - start, 3)
        report['predictions'].append(comparison)
        save(args.output, report)
        print(f"{len(report['predictions'])}/{len(rows)} {row['id']}", flush=True)
        if args.pause and row is not rows[-1]:
            time.sleep(args.pause)
    report['complete'] = True
    report['model_revision'] = getattr(getattr(indictrans2_adapter.model, 'config', None), '_commit_hash', None)
    report['processor'] = type(indictrans2_adapter.processor).__name__
    report['processor_version'] = getattr(indictrans2_adapter.processor, 'VERSION', 'upstream')
    report['assisted_examples'] = sum(row['paths'].get('roman_hybrid', {}).get('context_status') == 'assisted'
                                     for row in report['predictions'])
    report['roman_vs_canonical_local_output_differences'] = sum(
        row['paths']['roman_local'].get('translation_native') != row['paths']['canonical_local'].get('translation_native')
        for row in report['predictions'])
    report['note'] = 'Output differences are not necessarily errors; inspect paired predictions and source interpretation.'
    save(args.output, report)
    print(json.dumps({key: value for key, value in report.items() if key != 'predictions'}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
