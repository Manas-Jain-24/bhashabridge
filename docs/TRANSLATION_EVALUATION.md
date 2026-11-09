# Native-script translation evaluation

## Full GPU benchmark on 9 November 2026

All **6,072 translation cases** were evaluated: 1,012 frozen FLORES-200 devtest sentences in each of six directions, with **1 inference failure**. The final summary is marked `complete=true`, `diagnostic_subset=false`. Reports, predictions and low-scoring examples are in [the full GPU results](../ml/evaluation/expanded-gpu/summary.json).

| Direction | BLEU | chrF++ | Inference failures |
|---|---:|---:|---:|
| Hindi → Marathi | 13.78 | 44.10 | 0 |
| Hindi → Bengali | 15.32 | 44.25 | 0 |
| Marathi → Hindi | 23.95 | 47.80 | 0 |
| Marathi → Bengali | 14.90 | 43.27 | 0 |
| Bengali → Hindi | 20.23 | 44.47 | 0 |
| Bengali → Marathi | 11.06 | 40.19 | 1 |

The failed case is Bengali→Marathi at zero-based index 304: the adapter rejected a degenerate repeated fragment (`RepetitiveGenerationError`) even after the runner retried the example individually. This is a model-output failure, not a missing GPU or a discarded test case.

The RTX 4050 Laptop GPU ran the same cached distilled 320M checkpoint in float16, with 32-example batches, four CPU threads and the recorded five-beam decoding policy. Per-direction evaluation time totaled **28.1 minutes**, excluding model loading and the initial corpus audit; the complete command and finalization took **28.6 minutes**. PyTorch was `2.14.1+cu130`, CUDA runtime `13.0`. See [GPU setup and reproduction](GPU_BENCHMARK.md).

These scores are reference-similarity metrics, not correctness percentages. Failed examples remain empty predictions in the score denominator; they are not dropped or replaced with fallback answers. Other outputs passed the basic output guards, which does not establish semantic correctness. Precision and batch size differ from the earlier CPU diagnostic, and the full split has a different sentence distribution, so differences in scores are not evidence of a model-quality improvement.

The first 16 rows were inspected while debugging before this full run. The full-split score includes them; it is not a fresh untouched evaluation. Reviewed-memory overrides, Roman input, grammar explanations and generated English meanings are excluded. Our teaching/test overlap checks pass, but upstream pretrained-model exposure to FLORES is unknown. Human bilingual review remains necessary.

## Earlier CPU diagnostic

The six-direction runner evaluates the cached IndicTrans2 Indic-to-Indic distilled 320M checkpoint against FLORES-200 devtest. It bypasses reviewed-memory overrides, refuses a rule fallback, and records checkpoint revision, processor class, precision, generation arguments, corpus SHA-256, metric signatures, predictions and the lowest-scoring examples.

The local run uses **the first 16 source-order rows per direction**, not a random or representative sample. These rows are clustered in particular domains. It is a diagnostic for finding failures, not a language-wide accuracy estimate or a completed 1,012-row benchmark. Do not compare these figures with BLEU on a different dataset or with Bengali word-transliteration accuracy.

### Reproduce and resume

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_expanded_translation.py --all-pairs --offline --limit 16 --batch-size 4 --threads 4 --output-dir ml/evaluation/expanded-diagnostic
.\.venv\Scripts\python.exe scripts/finalize_translation_reports.py ml/evaluation/expanded-diagnostic
```

For the full frozen split, omit `--limit` and use a separate output directory. A compatible saved report resumes from the next unfinished batch; completed reports are marked `complete=true`. A completed diagnostic subset still does not mean the full split is complete. Current generation uses five beams, maximum length 256, disabled decoder cache, `no_repeat_ngram_size=4` and early stopping, with float32 CPU weights. The final diagnostic uses four-item batches/four threads. The older baseline configuration is kept separately in `ml/evaluation/translation-baseline-diagnostic/`; its Bengali-source reports are incomplete.

The app's native-script path and benchmark share sentence-final punctuation handling. A deterministic cleanup removes the old adapter's extra danda after punctuation inside closing quotes. The report finalizer applies the same cleanup to already-saved predictions, retains the old string when changed, and records scores before repair. It uses no reference-dependent rewriting and makes no additional model calls.

### Findings to take seriously

The completed diagnostic contains 96 translations: 16 in each direction, with no inference failures under the final decoding policy. These are prefix-sample results only.

| Direction | BLEU | chrF++ |
|---|---:|---:|
| Hindi → Marathi | 9.28 | 43.40 |
| Hindi → Bengali | 13.32 | 43.86 |
| Marathi → Hindi | 25.09 | 52.11 |
| Marathi → Bengali | 12.59 | 44.11 |
| Bengali → Hindi | 22.75 | 47.43 |
| Bengali → Marathi | 8.13 | 41.36 |

See [the machine-readable matrix](../ml/evaluation/expanded-diagnostic/summary.json). The full benchmark had not been run at the time of this CPU diagnostic. It has now completed on GPU, as recorded above; this earlier sample alone cannot establish general translation quality.

- The diagnostic exposed a punctuation bug: a translation ending in a punctuated closing quote received an additional `।`. The shared postprocessor now handles quoted endings, with seven regression cases.
- A Bengali-source baseline example repeated the same fragment until the token limit. Repetition controls now limit this behavior; a separate output guard rejects persistent degenerate loops. Failed inference stays in the denominator as an empty hypothesis with an error marker; it is never replaced with rule output or omitted from the score.
- The repetition constraint can also affect intentionally repeated phrases. It is a decoding tradeoff, not proof that the resulting translation preserves meaning.
- Generation now projects only the final decoder position into vocabulary scores, rather than every unused prefix position. A unit check verifies last-logit equivalence and hook restoration after failures; eight real baseline outputs matched exactly across four directions. Repetition controls are a separate decoding-policy change, so the final policy is evaluated separately rather than mixed with old scores.
- In the Hindi→Bengali sample at index 0, the prediction shifts the tense/negation relationship in a complex relative clause. A punctuation fix does not repair that meaning error.
- Low chrF can also reflect vocabulary choice rather than incorrect meaning: index 2's Bengali reference and prediction use different terms for diabetes. Automatic similarity requires bilingual interpretation.
- This benchmark excludes our teaching data, but we cannot establish whether the upstream pretrained model saw FLORES data. Roman input, names in conversational context, teaching-memory overrides and grammar explanations need separate evaluation.

The per-direction reports and machine-readable matrix are in `ml/evaluation/expanded-diagnostic/`. The finalizer refuses to combine different checkpoints, corpora, precision or decoding settings. Each metric is a corpus-level SacreBLEU BLEU (`intl` tokenizer) or chrF++ (`word_order=2`) value for its diagnostic subset. There is no general translation accuracy percentage. The first sixteen test rows have now been inspected for debugging; future claims about unseen quality should use the uninspected remainder or a newly frozen independent benchmark.
