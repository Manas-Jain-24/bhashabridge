# Translation quality experiment v1

This experiment audits the earlier six-direction FLORES benchmark, repairs concrete preprocessing/output defects, trains a Bengali→Marathi LoRA candidate, selects an epoch on validation only, and evaluates the fixed choice on a separately frozen news test. Training loss is not a translation-quality score. The existing 6,072-case benchmark remains unchanged and is never imported into training or reviewed translation memory.

## Audit and corrections

[`quality-audit-v1/audit.json`](../ml/evaluation/quality-audit-v1/audit.json) summarizes a 263-example review queue drawn from low chrF scores, heuristic flags and a seeded sample across all six directions. Each queued example includes its source, prediction, reference, English reference and flags. Numbers and acronym flags identify possible problems, not confirmed semantic-error counts. Five observations are provisionally annotated; the remaining queue is pending bilingual review. No native-speaker approval is claimed.

Confirmed technical defects include missing digit/entity handling in the Windows processor and acceptance of unresolved model placeholders. A live-path check also found that transliteration corrupted URLs and emails before translation; a shared entity matcher now protects those spans in both transliteration directions. The processor normalizes decimal digits and punctuation, protects URLs, emails, formatted numbers and handles with per-sentence maps, restores known placeholder variants, clears state after failed requests, and rejects dropped protected entities. Output guards reject unresolved ID markers and corrupted omega/digit runs while allowing literal markers present in the source. These guards cannot prove that the rest of a translation preserves meaning.

[`translation_corrections_v1.jsonl`](../data/curated/translation_corrections_v1.jsonl) contains **94 locally authored draft pairs**, including templated numeric variations, negation, gender-explicit past/future examples, names, time, decimal amounts, URLs and email addresses. They were written independently of held-out references, labelled `author_draft_not_native_reviewed`, and never promoted into the app's reviewed-memory table. They need bilingual correction before being described as reviewed data.

## Data separation

The base training file contains 997 Bengali→Marathi pairs from the existing FLORES-200 **dev** teaching corpus. Training adds the separate 94 correction drafts, giving **1,091 pairs**. The frozen base manifest retains its original count of 997; the training configuration records the additional correction file and its checksum separately.

Fresh validation/test references come from [MicrosoftTranslator/NTREX](https://github.com/MicrosoftTranslator/NTREX), revision `468c6b69c7f6a75d31d4743d9daba2af566cc18d`, under CC BY-SA 4.0. The importer joins line-aligned Bengali, Hindi, Marathi and English files with document IDs. It excludes sentences overlapping existing teaching/benchmark files, sorts whole documents by a fixed SHA-256 policy, and freezes **78 validation** and **139 test** multiway rows. Documents are disjoint between the two splits. No NTREX reference is intentionally used as training data. File hashes and normalized source/target overlap are checked before training and evaluation.

This is a document-separated **subset of NTREX news**, not the full NTREX benchmark or a representative conversational evaluation. Exposure of upstream pretrained weights to NTREX/FLORES is unknown. Fresh means unused by this project's adaptation and model-selection work. This experiment does not measure Roman input, reviewed-memory lookup, explanations, English meanings or pronunciation.

Citation: Federmann, Kocmi and Xin (2022), [NTREX-128](https://aclanthology.org/2022.sumeval-1.4/); Barrault et al. (2019), [WMT19 findings](https://aclanthology.org/W19-5301/). Original FLORES data: [FLORES-200](https://github.com/facebookresearch/flores). The redistributed NTREX license is included beside the frozen corpus.

## Training and selection protocol

The cached IndicTrans2 distilled 320M checkpoint is frozen. PEFT trains rank-8 LoRA matrices on attention `q_proj` and `v_proj` modules: **884,736 trainable parameters**, alpha 16, dropout 0.05, AdamW at 0.0001, two epochs, microbatch one and gradient accumulation eight. Seed is 42. Base weights use float16; trainable adapter weights use float32. Training excludes rather than truncates examples longer than 128 tokens; no examples in this run exceeded that limit. Both checkpoints and the complete configuration are retained in [`translation-lora-v1`](../ml/experiments/translation-lora-v1/).

Both saved epochs are scored on the 78-row Bengali→Marathi validation split. The best validation chrF++ selects the candidate, with BLEU/failures and the earlier epoch as tie-breakers. It must gain at least 0.5 chrF++, lose no BLEU and add no failed examples to pass the validation gate. Selection and the checkpoint hash are saved **before** the fresh test is evaluated. The test gate requires a positive chrF++ gain, no more than 0.5 BLEU loss and no additional failed examples. These are predefined engineering gates, not statistical proof of broad improvement.

The fixed baseline is tested in all six directions; the chosen adapter is tested only for Bengali→Marathi. Other directions must continue using base weights. An unsuccessful candidate remains an experiment rather than becoming the default model. Failed examples remain empty hypotheses in the score denominator. Every report records split/model/checkpoint identity, precision, processor version, decoding settings, predictions, metric signatures and failures.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-training.txt
.\.venv\Scripts\python.exe scripts/prepare_translation_quality.py --audit
.\.venv\Scripts\python.exe scripts/audit_translation_quality.py
# Use a new experiment directory for a new training run; do not overwrite results.
.\.venv\Scripts\python.exe scripts/train_translation_adapter.py --output ml/experiments/translation-lora-v2
# Reproduce evaluation of the completed v1 artifacts:
.\.venv\Scripts\python.exe scripts/run_translation_quality_experiment.py --skip-training
```

The frozen splits are checked into the repository; `prepare_translation_quality.py --download` creates them only when no manifest exists. It refuses silent resampling. CUDA-enabled PyTorch and cached base weights are required; [GPU setup](GPU_BENCHMARK.md) documents the local RTX 4050 configuration. No Gemini calls are made for training or this evaluation.

## Results

The complete run trained two checkpoints and evaluated the previous/fixed processors on validation, both adapters on validation, and the fixed baseline in all six directions on the fresh test. Epoch 2 was selected using validation only. **The adapter was not promoted**: its validation chrF++ gain was 0.35, below the predefined 0.5 threshold. The running app uses the base model with the entity/output fixes.

| Bengali→Marathi comparison | BLEU | chrF++ | Failed cases |
|---|---:|---:|---:|
| Validation baseline (78) | 7.40 | 40.34 | 0 |
| Validation selected epoch (78) | 7.90 | 40.70 | 0 |
| Fresh test baseline (139) | 8.47 | 39.12 | 2 |
| Fresh test selected epoch (139) | 9.31 | 38.88 | 3 |

The independent test is reported even though the validation gate already rejected promotion. Its outcome did not change the selected epoch or trigger another tuning run. Similarity differences are not correctness percentages, and this single small news-domain experiment does not establish a statistically reliable or general improvement.

Fresh test results for the **fixed baseline**:

| Direction | BLEU | chrF++ | Failed cases / 139 |
|---|---:|---:|---:|
| Hindi → Marathi | 11.35 | 42.80 | 4 |
| Hindi → Bengali | 12.68 | 42.21 | 5 |
| Marathi → Hindi | 21.67 | 45.88 | 0 |
| Marathi → Bengali | 12.77 | 41.65 | 6 |
| Bengali → Hindi | 17.68 | 41.72 | 0 |
| Bengali → Marathi | 8.47 | 39.12 | 2 |

The stronger guards can reject outputs that omit protected entities. Those cases stay in the denominator as empty predictions; they are not substituted with translation-memory or rule answers. This is a visible reliability/coverage tradeoff, not proof that all accepted outputs are correct. The earlier processor comparison on the separate validation split showed only small score changes; no broad accuracy gain is claimed for the code fixes.

Live API smoke checks passed after the final transliteration-stage fix: an unseen Bengali sentence produced Marathi plus “We will meet again on Friday.”, and a separate Hindi→Marathi request preserved `https://example.org/team` exactly. Both used the neural base model with no rule fallback. Cached evaluation reports were also reused without regenerating the frozen predictions.

Training took 8.5 minutes with 0.80 GiB peak allocated GPU memory. The final backend suite passed **200 tests**. Artifacts: [decision](../ml/experiments/translation-lora-v1/decision.json), [training report](../ml/experiments/translation-lora-v1/training_report.json), [fresh baseline reports](../ml/evaluation/quality-v1/test-baseline/summary.json), [fresh candidate report](../ml/evaluation/quality-v1/test-candidate/summary.json).

Next data work is native bilingual review of the correction drafts and flagged examples. Future adaptation should use new versioned training data and a newly frozen independent test; this test is now observed and must not be reused to advertise an untouched evaluation.
