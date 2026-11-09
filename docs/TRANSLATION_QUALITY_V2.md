# Translation quality v2: larger corpus and controlled adaptation

This work expands the Bengali→Marathi training corpus, completes a provisional review of the earlier error queue, and compares learning rates, adapter ranks and training duration. Automatic metrics and AI judgments remain separate from human approval.

## Data provenance and scope

The corpus contains **6,997 distinct pairs**: 2,000 from BPCC-H-Daily, 4,000 from BPCC-H-Wiki and 997 general reference pairs from FLORES-200 dev. The 94 locally authored, unreviewed correction drafts are excluded. BPCC files are pinned to revision `5bde309374f21c39e7c3d505f28ae11f58f2a220`.

BPCC supplies human-translated **English→Bengali** and **English→Marathi** sentences. We join only exact shared English sources after NFC/whitespace normalization, preserve case and punctuation, drop conflicting translations and filter native-script/length problems. We do not align by row number or use generated Marathi references. These are **English-pivot human translations, not locally reviewed direct Bengali→Marathi pairs**; sense, gender and context ambiguity can remain.

The importer found 2,694 Daily and 39,743 Wiki shared sources before subsequent corpus filters. It freezes separate BPCC validation/test sets of 160 pairs each, balanced equally between Daily and Wiki. Native source, target and English aliases are kept disjoint across splits. BPCC was used in IndicTrans2 pretraining, so these holdouts measure local adaptation and possible forgetting, not performance on unseen pretraining data.

For an additional check, **74 validation and 150 test news sentences** come from previously unused NTREX documents. Earlier v1 validation/test documents, old test sentences and teaching overlap are excluded. New news splits are document-disjoint. Upstream pretrained exposure is unknown; “unused” refers to this project's local adaptation. This remains a limited news subset, not all NTREX or general translation accuracy.

All five frozen files have byte-level hashes. The builder refuses resampling an existing manifest, never pads a short corpus with synthetic pairs, and audits source/target/English overlap before training. Training examples do not enter the application's reviewed translation-memory database.

Sources and terms:

- [AI4Bharat BPCC](https://huggingface.co/datasets/ai4bharat/BPCC), BPCC-H-Daily/Wiki: CC BY 4.0; Gala et al. (2023), [IndicTrans2](https://arxiv.org/abs/2305.16307). Access requires an authorized Hugging Face account. Credentials are local environment settings and are never included in artifacts.
- [MicrosoftTranslator/NTREX](https://github.com/MicrosoftTranslator/NTREX), revision `468c6b69c7f6a75d31d4743d9daba2af566cc18d`: CC BY-SA 4.0. Cite Federmann, Kocmi and Xin (2022), [NTREX-128](https://aclanthology.org/2022.sumeval-1.4/), and Barrault et al. (2019), [WMT19](https://aclanthology.org/W19-5301/).
- [FLORES-200](https://github.com/facebookresearch/flores): CC BY-SA 4.0. Only dev teaching references are training replay; devtest is blocked.

## Review work

All **263 selected audit examples** received a provisional Gemini review with categories for meaning, negation, tense, person/gender, names, numbers, omission, hallucination, repetition, placeholders and reference variation. The machine classified 134 as likely errors and 129 as acceptable alternatives. These are one model's judgments of a deliberately selected queue, **not an error rate or ground truth**. No example received human approval and no benchmark text was exported into training. IDs and input hashes are checked on resume; malformed/duplicate/unknown responses are rejected.

The [94-draft review CSV](../data/review/translation-corrections-v1.csv) is a separate human workflow. A reviewer can mark `accept`, `revise` or `reject`, provide their identity/date and put revisions in `corrected_target_text`. Import requires an explicit `--attest-human-review` flag, preserves the original drafts, refuses overwritten source/identity fields and blocks frozen benchmark overlap. This records a submitted attestation; it does not independently authenticate the reviewer's proficiency. It never modifies the app database automatically.

## Predeclared comparison

| Profile | Rank | Learning rate | Epochs retained |
|---|---:|---:|---:|
| Conservative reference | 8 | 0.00005 | 1 and 2 |
| Learning-rate comparison | 8 | 0.0001 | 1 |
| Capacity comparison | 16 | 0.00005 | 1 |

All profiles use the same frozen corpus, seed 42, attention q/v LoRA modules, alpha twice rank, dropout 0.05, microbatch four and accumulation four (effective batch 16). Base weights remain frozen. Inputs over 128 tokens are excluded rather than silently truncated; the report records all exclusions. Equal one-epoch checkpoints compare rank/learning rate; the conservative profile's second epoch checks duration. This is a bounded experiment, not an exhaustive hyperparameter search.

The protocol is saved before validation. Candidate selection uses validation-domain chrF++ with news non-regression; gates require at least 0.5 domain chrF++ gain, no BLEU loss, no more than 0.5 news chrF++ loss and no additional failed examples on either split. The chosen checkpoint hash and data-manifest hash are frozen before either final test runs. The same test gates determine the numeric promotion recommendation. Failed outputs remain empty hypotheses in the denominator. There is no repeated test-driven tuning.

An initial training attempt saved its first checkpoint and then failed while reporting a relative output path. It was preserved locally and excluded from model selection. The output-path bug was fixed in both training commands, regression-tested, and the same profile restarted from the base model with unchanged data/seed. Only completed reruns are eligible candidates.

After numeric testing, a separate blind AI comparison can assess meaning. A/B order is randomized, model identities are hidden and source meaning takes priority over wording similarity. It checks omissions, additions, negation, tense, entities and broken output. This is diagnostic, not native-human certification or a source of new training examples.

## Runtime safeguards

A separate cache/memory regression was fixed during this work: source text is no longer case-folded for the neural/fallback result cache, and normalized reviewed-memory matches are rejected when their opaque entities differ. This prevents case-sensitive URL paths such as `/Team` and `/team` from sharing the wrong answer. Existing native-script benchmark metrics bypass these runtime lookups and are unaffected by that change.

The optional `INDICTRANS2_ADAPTER_DECISION` setting points to a completed local decision file. The loader rechecks validation/test gates, supported language scope, base checkpoint revision and adapter bytes. Paths must remain inside the project. Only Bengali→Marathi can use the adapter; other directions temporarily disable it under the inference lock, with state restored after errors. An unapproved or mismatched artifact cannot silently become active. Training and evaluation explicitly disable deployed adapters so baselines remain clean. The production setting remains unset until final checks justify activation.

## Commands

```powershell
.\.venv\Scripts\python.exe scripts/prepare_translation_quality_v2.py --audit
# Download/build only before the v2 manifest exists:
.\.venv\Scripts\python.exe scripts/prepare_translation_quality_v2.py --download
.\.venv\Scripts\python.exe scripts/review_translation_quality.py
.\.venv\Scripts\python.exe scripts/run_translation_quality_v2.py
# After numeric evaluation finishes:
.\.venv\Scripts\python.exe scripts/judge_translation_candidates.py
# Export requires a new destination; existing reviewer edits are never overwritten:
.\.venv\Scripts\python.exe scripts/curate_translation_corrections.py export --output data/review/new-review.csv
# Only a human reviewer should attest/import completed decisions:
.\.venv\Scripts\python.exe scripts/curate_translation_corrections.py import --input data/review/new-review.csv --output data/curated/reviewed-corrections-v2.jsonl --attest-human-review
```

Install `backend/requirements-training.txt` and a compatible CUDA PyTorch build first. Frozen processed files are included in the repository. Raw corpus files, API keys, download caches and local logs are excluded. Training/checkpoint reports and final test results are retained for review.

## Results

**The larger-corpus experiment did not produce an approved replacement.** All four completed checkpoints failed the predefined validation gates. The highest domain-validation checkpoint, `rank8-lr1e-4-epoch-1`, was retained only for the final diagnostic test; it was already ineligible for deployment before that test ran. The active application keeps the base weights, with the cache/entity fixes.

| Checkpoint | Domain chrF++ | News chrF++ | News failures | Passed validation gates |
|---|---:|---:|---:|---|
| Base model | 51.21 | 33.08 | 2 | Reference |
| rank8-lr5e-5-epoch-1 | 50.56 | 34.10 | 2 | No |
| rank8-lr5e-5-epoch-2 | 50.60 | 32.96 | 3 | No |
| rank8-lr1e-4-epoch-1 | 50.78 | 32.88 | 3 | No |
| rank16-lr5e-5-epoch-1 | 50.77 | 32.70 | 3 | No |

Fresh reserved test results:

| Evaluation | BLEU | chrF++ | Failed cases |
|---|---:|---:|---:|
| BPCC local-adaptation test (160) — baseline | 24.26 | 53.10 | 0 |
| BPCC local-adaptation test (160) — diagnostic candidate | 23.72 | 52.46 | 0 |
| New NTREX news test (150) — baseline | 10.82 | 41.47 | 2 |
| New NTREX news test (150) — diagnostic candidate | 12.07 | 41.29 | 7 |

The selected candidate's news BLEU increased, but domain BLEU/chrF++ decreased and news failures rose from 2 to 7. These mixed results do not establish improved translation accuracy. No gate was relaxed, no different checkpoint was selected from test scores, and no model was enabled merely because more training data had been collected.

The blind provisional AI comparison covered **310 cases**. Preference counts were {"baseline": 64, "candidate": 83, "tie": 157, "uncertain": 6}; the judge marked 61 baseline and 32 candidate outputs as having major errors. These remain unverified machine judgments, not correctness rates or bilingual-human approval. Temporary provider 503 errors and free-tier rate limits were handled by saved progress, bounded backoff and request pacing; completed cases were not silently dropped.

Successful training totaled 31.6 minutes across the three profiles, with 1.32 GiB peak allocated GPU memory. The supervisor completed training, validation selection and reserved numeric tests in 48.3 minutes, excluding the preserved incomplete first attempt. The final backend suite passed **219 tests**. Model artifacts, exact configurations, input hashes, per-example predictions, decisions and provisional judgments are retained.

Live API smoke checks passed after restart: Bengali→Marathi produced Marathi plus an English meaning, and separate requests preserved `https://example.org/team` and `https://example.org/Team` without a cache collision. All three used base neural weights with no rule fallback. The optional adapter setting remains unset.

Artifacts: [frozen corpus manifest](../data/processed/translation-quality-v2/manifest.json), [decision](../ml/experiments/translation-quality-v2/decision.json), [semantic comparison](../ml/evaluation/quality-v2/semantic-judgment/summary.json), [263-example provisional review](../ml/evaluation/quality-review-v2/summary.json), [model card](../ml/experiments/translation-quality-v2/MODEL_CARD.md).

The next training-data priority is new, directly reviewed Bengali→Marathi examples targeting actual meaning failures. Repeating sweeps on the now-observed test sets would not create fresh evidence. Human review is still pending for the local drafts and joined pairs; the review CSV/import tool makes that work explicit rather than manufacturing approved labels.
