# Automated roadmap work — 12 November 2026

The non-review infrastructure is implemented. Human judgments, a new trained
model and public deployment are not claimed. The strongest measured result is a
general preprocessing fix: the same 600-request diagnostic batch went from **22
runtime errors and 24 protected-value failures to zero of either**. This is not
a translation-accuracy percentage.

## What changed

| Roadmap area | Implemented | Remaining gate |
| --- | --- | --- |
| Evaluation | 50 intents per direction, 600 native/Roman requests, grouped frozen splits, hashes, resumable isolated runner, per-direction reports | Independent bilingual references and a fresh unseen test batch |
| Corrections | Report/proposal/review/rejection states, role checks, version conflicts, provenance/rights, audit history, gated exports and explicit memory publication | Actual human review; none generated |
| Targeted intervention | General entity masking for signed/leading-decimal values, Bengali placeholder recognition, occurrence-count validation | Semantic adequacy and broader distribution checks |
| Reliability | Browser CI, deterministic backend tests, bounded live smoke, total deadlines, stage metrics, provider observations, fallback counts | Deployment-sized load tests and durable external monitoring |
| Learner data | Accounts, CSRF, resource ownership, replay-safe rewards, rate/provider quotas, export/deletion | Deployment operator, HTTPS and retention policy |
| Database | Ordered additive migration, backup/restore tool, verified restore drill, expiry maintenance | Rehearse each future migration in staging |
| Future languages | Shared registry checks, per-direction draft coverage and onboarding instructions | Reviewed language content; no new language advertised |

The local workspace remains accessible without registration only on loopback.
Set `AUTH_MODE=accounts` to use the new sign-in flow. The existing learner's
progress was preserved. The local correction queue contains **300 unreviewed
evaluation proposals and 300 draft-import events**, not trusted translation rows.
The existing 660 translation-memory rows were unchanged by the import.

The explanation engine no longer falls back to the retired legacy explanation
branch after an error. It returns an explicit unavailable explanation. UI changes
include malformed-response validation, dialog focus containment/restoration,
long-identifier wrapping, account session handling, correction pagination and a
usable message when no matching speech voice exists. Browser testing caught and
fixed the registration form remaining selected after sign-out.

## Measured root cause and intervention

The first full run reproduced failures systematically. Numeric protection only
recognized certain multi-part numbers and skipped short formats. `.5` reached the
model as ordinary punctuation plus `5`, and signed values could be separated by
detokenization. Bengali generation rendered the placeholder as `आइडि`, while the
restoration regex recognized other spellings of ID. The model had retained the
marker, but the application rejected it as a lost identifier.

The fix expands the shared entity tokenizer to signed numbers, leading decimals,
percentages and long integers. Those values travel through model/script conversion
as protected placeholders and are restored after detokenization. The processor
recognizes bounded ID spelling variants and requires each protected occurrence
exactly once. Missing or duplicated markers still fail validation; arbitrary
model text is not guessed into a value. No sentence-specific translation rule or
new model weight was added.

Both local runs used 50 native and 50 Roman requests in every direction, the real
IndicTrans2 model and zero Gemini calls. There were **zero memory hits** in either
run. The corrected run used an RTX 4050 Laptop GPU, float16, PyTorch 2.14.1+cu130;
model revision `ffb7582b6d43791f1fb26b2153fc065f2e9ea575`.

| Direction | Before errors / 100 | Before value failures | After errors / value failures | Native p95 | Roman p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hindi → Marathi | 0 | 4 | 0 / 0 | 0.398 s | 0.614 s |
| Hindi → Bengali | 10 | 4 | 0 / 0 | 0.422 s | 0.592 s |
| Marathi → Hindi | 0 | 4 | 0 / 0 | 0.405 s | 0.609 s |
| Marathi → Bengali | 10 | 4 | 0 / 0 | 0.373 s | 0.577 s |
| Bengali → Hindi | 0 | 4 | 0 / 0 | 0.380 s | 0.444 s |
| Bengali → Marathi | 2 | 4 | 0 / 0 | 0.363 s | 0.381 s |

Latency is serial runtime timing on this machine, not a concurrent HTTP load test.
The first cold request took **7.958 seconds** including model loading; it is retained
in the report. Warm distributions and stage timings are recorded separately.
All 600 corrected requests returned a result, but grammatical/meaning errors can
still exist. Draft exact matches and source CER are not scored as reviewed accuracy.
These examples were inspected to diagnose bugs, so the improvement is a regression
result, not a claim about untouched held-out data.

Reports retain complete synthetic requests, outputs and failures:

- [Original 600-request baseline](../data/quality/reports/local-runtime-2026-11-12.json)
- [Corrected 600-request run](../data/quality/reports/local-runtime-entities-v3-2026-11-12.json)
- [Six-direction provider smoke](../data/quality/reports/provider-smoke-2026-11-12.json)
- [Budgeted 300-request hybrid run](../data/quality/reports/hybrid-budgeted-2026-11-12.json)
- [Structural comparison and supporting-view checks](../data/quality/reports/structural-comparison-2026-11-12.json)
- [Model promotion correctly blocked](../data/quality/reports/promotion-blocked-2026-11-12.json)

The six-call provider-only probe returned validated assisted responses in all six
directions. It used a maximum of 2,048 output tokens per call and no retries. This
confirms the configured key worked during this run; it does not guarantee future
availability or answer correctness. Regular CI makes no paid calls.

The separate full hybrid run completed **300/300 requests with zero protected-value
failures**, while respecting its six-call ceiling. Only **4 were assisted**;
296 returned labelled local fallback: 2 provider errors, 158 circuit-cooldown
responses and 136 exhausted-budget responses. The persistent run counter ended
at exactly 6. The failures are retained, rather than retried until the report
looks successful. These numbers test availability/fallback handling, not hybrid
translation quality or a natural production fallback rate.

Supporting-view checks found no protected-value losses in source estimates, native
translations or Roman output after the fix. Local-mode English meanings were
unavailable for all 600 examples, as expected without cloud or memory meanings.
Local Bengali grammar explanations were also unavailable. The UI labels those
absences; they are not counted as successful explanations or glosses.

## Validation and operations

- **294 backend tests passed** locally, including two-user isolation, replay,
  CSRF, review permissions/conflicts, deadlines, quota persistence and migrations.
- **6 Chromium browser tests passed**; the production frontend build passed.
- Corpus leakage, expanded-data hashes and language structural checks passed.
- The promotion command exited with a rejection because independent review and
  held-out-only quality evidence are absent. No model was promoted or trained.
- One existing Starlette/httpx deprecation warning remains in the test environment.

The browser suite covers account creation/sign-out, real API translation in
mock-model mode, a correction proposal, language swap, provider outage, malformed
response, input/mode changes while a request is pending, empty input, 390px layout,
long URLs, clipboard denial, modal focus, unavailable audio and Bengali round
completion. It uses a separate temporary database and retains failure artifacts.

The restore drill copied the migrated database and compared integrity, table counts
and SHA-256. Backup and restored database both produced
`078f9b4adfe9dd176ee910296d088e89cc36eb3ab64458beb2a2bd512bfac625`.
Private database files remain in ignored `.demo/backups`; they are not published.
The pre-migration backup is retained separately. New database code refuses to
overwrite live data or run against a newer schema.

See [operations](OPERATIONS.md) for environment separation, quotas, maintenance,
privacy, migration/rollback and deployment checks. See the [evaluation protocol](../data/quality/README.md)
for reproducible commands and the human-review annotation contract.

## Next engineering work

Use the review queue to obtain independent source/target judgments before training
again. Establish a fresh unseen test batch before claiming semantic improvement.
Keep the current Hindi/Marathi/Bengali scope; English remains a supporting gloss.
Choose a translation/transliteration intervention from reviewed error categories,
retain the current model as rollback, and reject candidates that regress a
direction or critical intent/entity/negation slice. The new infrastructure makes
those decisions reproducible; it cannot supply the missing human judgments.
