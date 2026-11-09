# Bengali→Marathi LoRA v1 — experimental, not deployed

This is a pair-specific adapter for `ai4bharat/indictrans2-indic-indic-dist-320M`, base revision `ffb7582b6d43791f1fb26b2153fc065f2e9ea575`. It is not a standalone translation model. Base weights remain unchanged and are not redistributed here.

Two rank-8 attention q/v LoRA checkpoints were trained on 997 FLORES-200 dev references and 94 independently authored correction drafts. The drafts have **not** received native-speaker review. No FLORES devtest or NTREX reference was used for gradients. Training used seed 42, two epochs, 884,736 trainable parameters, AdamW at 0.0001, microbatch 1 and accumulation 8. Full recipe/input hashes are in `training_config.json` and `training_report.json`.

Validation selected epoch 2, but its chrF++ gain (0.35) did not meet the frozen 0.5 threshold. **Do not treat this artifact as an approved replacement for the base model.** The application does not load it by default.

On the 139-example document-disjoint NTREX test, baseline BLEU/chrF++ were 8.47/39.12; the selected candidate scored 9.31/38.88, with 3 failed examples included as empty hypotheses. This is a news subset, not all NTREX or a general accuracy percentage. Upstream pretrained exposure is unknown. No further test-driven tuning was performed.

Scope: Bengali→Marathi research only. Other language directions were not adapted. The candidate still needs broader independent evaluation and bilingual data review. Source references retain their CC BY-SA 4.0 terms; see the [data and experiment report](../../../docs/TRANSLATION_QUALITY_V1.md) for attribution and limitations.
