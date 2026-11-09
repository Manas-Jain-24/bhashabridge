# Bengali→Marathi adaptation v2 — evaluated, not deployed

Status: **No checkpoint passed promotion. Production retains base weights.**

Base: `ai4bharat/indictrans2-indic-indic-dist-320M`, revision `ffb7582b6d43791f1fb26b2153fc065f2e9ea575`. These files contain PEFT LoRA weights only; the base model is not redistributed.

Data: 6,997 distinct training pairs (2,000 BPCC-H-Daily, 4,000 BPCC-H-Wiki, 997 FLORES dev replay). BPCC pairs join human English→Bengali and English→Marathi translations by exact shared English source, after removing ambiguous mappings and benchmark overlap. They are not locally reviewed direct Bengali→Marathi pairs. The 94 local draft corrections were excluded. BPCC may already have been used in base-model pretraining.

Profiles: rank8/lr0.00005 for two epochs, rank8/lr0.0001 for one epoch, rank16/lr0.00005 for one epoch. All use seed42, q/v LoRA, alpha twice rank, dropout0.05, microbatch4, accumulation4, max128tokens and frozen base weights. Four retained checkpoints were scored on validation only before the final diagnostic choice was frozen.

All four missed validation gates. The diagnostic candidate was `rank8-lr1e-4-epoch-1` with adapter SHA256 `6e91fbb23f86e5b08988677d0f7ccc777d66247c114d32a160fc6e647d2ebf16`. Its BPCC-test chrF++ was 52.46 versus 53.10 for baseline; its news-test failures were 7 versus 2. Do not label it an improved or approved model.

Tests:160 BPCC pairs and150 previously unused local NTREX news sentences. BPCC holdouts measure local adaptation, not unseen pretraining data. Upstream NTREX exposure is unknown. The AI semantic comparison is provisional, not human certification or a general accuracy estimate. No test-based retuning was performed.

See [the full experiment](../../../docs/TRANSLATION_QUALITY_V2.md), protocol.json, selection.json, decision.json and each profile's training_config/training_report for recipes, source attribution and failures. BPCC source text is CC BY4.0; FLORES/NTREX text is CC BY-SA4.0. See the linked report for original authors and source repositories. A reporting-path failure in the incomplete first attempt was preserved locally, recorded in training_events.json and excluded from selection.
