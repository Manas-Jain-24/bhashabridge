# Runtime evaluation and review artifacts

`evaluation-draft-v1` is a frozen, **AI-authored, unreviewed** diagnostic set:
50 intents × six directions × native/Roman input = 600 runtime requests. It
covers Hindi, Marathi and Bengali. English is an explanatory view, not a newly
supported translation direction. There are 10 development intents and 40 test
intents; semantic families and all direction/spelling siblings share a split.
SHA-256 hashes and provenance are in the manifest. Never edit a frozen version;
create a new version for source corrections. Git preserves these files' bytes.

The first run is a diagnostic baseline. Reading failures to debug this batch means
the affected examples are regression evidence, **not an untouched estimate of
generalization**. Before claiming quality gains, collect independently reviewed,
previously unseen intents and freeze a fresh held-out evaluation. Pretraining
overlap in third-party models cannot be ruled out. Runtime memory hits are
reported separately and must not be represented as neural inference successes.

## Reproduce diagnostics

Run from the repository root with neural dependencies and cached model weights:

```powershell
python scripts/runtime_evaluation.py --mode local --output output/local-baseline.json
python scripts/runtime_evaluation.py --mode hybrid --max-cloud-calls 6 --output output/hybrid-baseline.json
python scripts/runtime_evaluation.py --mode local --output output/local-baseline.json --resume
```

Local mode runs 600 requests with **zero cloud calls**. Hybrid mode runs 300 Roman
requests with a persistent total call ceiling; budget exhaustion is a labelled
fallback, not an assisted success. Add `--split development` for iterative work.
Outputs, failed attempts and a separate SQLite evaluation database persist beside
the report. Keep that database when resuming so the provider budget cannot reset.
Resume refuses changes to code, data, mode, settings or runner protocol. Existing
reports are never silently overwritten. Requests in these reports are synthetic
evaluation text, not private learner input.

The report retains native source estimates, translations, Roman/English views,
explanations, model provenance, per-request latency and protected-value checks.
Native requests isolate input reconstruction from Roman requests; both still run
the real coordinator. Report memory hits explicitly. For strictly direct model
experiments use the existing `IndicTrans2Adapter.translate_native_batch` interface
and the training evaluation scripts, which forbid model fallback.

CER and exact matches against draft strings are debugging signals only. They are
not accuracy measurements. Accepted paraphrases, ambiguity, politeness and meaning
need independent annotation. Reports set `accuracy_score=null` and
`promotion_eligible=false` until reviewed evidence exists.

## Review workflow, when people are available

The UI supports reported → proposed → reviewed/rejected states, named reviewer
accounts, optimistic version conflicts, provenance, licensing and immutable event
history. A reviewed entry edited again becomes an unreviewed proposal. Nothing is
automatically added to trusted memory or training. Only an explicitly assigned
reviewer can attest to a review. No such decisions were made for this batch.

```powershell
python scripts/review_workflow.py import-drafts --owner-id 1
# Later, after a named bilingual reviewer creates an account:
python scripts/review_workflow.py set-reviewer --username reviewer_name
python scripts/review_workflow.py export-evaluation --output output/reviewed-evaluation.json
python scripts/review_workflow.py export-training --output output/reviewed-training.json
python scripts/review_workflow.py publish-memory --report-id REPORT_UUID
```

Draft import is idempotent. It imports 300 proposals, never approvals. Future
reviewers must verify native/Roman source spellings as well as target text; record
acceptable alternatives, unacceptable meaning changes and clarification needs in
the review note. A wrong frozen source requires rejection and a new dataset
version, rather than silently rewriting the baseline. Exported decisions retain
reviewer ID, date and audit event. A separate annotation artifact grades each
baseline/candidate result; a translation-reference review is not a model grade.

Training/memory publication require reviewed runtime content, an explicit accepted
redistribution license and no exact frozen native/Roman source or target overlap.
Human dataset preparation must additionally group semantic paraphrases; an exact
string filter cannot detect every paraphrase. Evaluation reports are never ingested
as teaching/game/training rows. Existing legacy manual import tools remain operator
utilities; use this audited workflow for new contributions.

## Promotion gate

`scripts/check_runtime_promotion.py` compares identical request matrices, requires
held-out test rows, independently recorded annotations bound to both report hashes,
at least 20 reviewed samples per reported slice, no per-direction adequacy
regression, an overall improvement, no new critical error, no structural failure,
and the specified p95 latency budget. It writes a decision; it does not deploy.

Each review has `id`, `path`, `reviewer`, `reviewed_at` and Boolean
`baseline_adequate`, `candidate_adequate`, `baseline_critical`, `candidate_critical`.
The wrapper has `human_reviewed=true`, `baseline_sha256`, `candidate_sha256` and
`reviews`. These fields are for actual human judgments, never generated approvals.
Keep unacceptable changes, ambiguity and supporting-view/explanation judgments
in additional annotation fields; publish the rubric and all direction counts.

```powershell
python scripts/check_runtime_promotion.py --baseline output/base-test.json --candidate output/candidate-test.json --reviews output/human-annotations.json --max-p95 60 --output output/decision.json
python scripts/check_language_readiness.py
```

The language check validates metadata, script examples, content availability and
50 draft cases per registered direction. It always reports the current human
quality gate as pending. Passing it is structural readiness, not language approval.
