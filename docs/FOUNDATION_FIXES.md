# BhashaBridge: foundation fixes

Implemented 24 October 2026. This pass repairs the existing learning workflow; stronger translation and a broader product redesign remain separate work.

## What changed

- **Startup:** Vite defaults to FastAPI on port 8000 and supports a `BACKEND_URL` override. The frontend launcher can use `node.exe` on PATH when npm is unavailable. Node requirements now match the installed Vite version.
- **Practice grading:** Multiple choice submits an option ID, evaluated against a server-owned correct option. The correct “Tomorrow / Kal” answer is also accepted by older text clients. Whitespace is normalized without stripping Devanagari marks.
- **Usable roadmap:** The practice dataset path is corrected. Curated examples supply enough distinct exercises at every level. Practice opens the active milestone; credited questions are excluded from that day's generated deck. Correct answers advance only the matching topic and difficulty. Replays receive no extra credit that day, and the final milestone completes without overflowing.
- **Real review dates:** A per-learner `vocabulary_reviews` table stores review timestamps, next-due timestamps, repetition counts, and Leitner boxes. Due counts can reach zero. Words reappear after their interval; already-reviewed submissions cannot repeatedly collect XP.
- **Speech checks:** Unicode combining marks and vowel signs are preserved; token order and repeated words affect scoring. Empty speech returns a valid zero result. Input length is bounded. The UI describes transcript matching honestly and uses native text for text-to-speech.
- **Rewards:** Server-checked answers determine scramble, scenario, and blitz rewards. Arbitrary XP/badge mutation is rejected. Chests are limited to one per UTC day; scramble/scenario completion rewards are deduplicated. Blitz XP is based on improvements to that day's best server-computed score. Qualifying daily missions award their bonus once.
- **Honest progress:** New learners begin at Level 0 with no earned XP, badges, or invented streak. Roadmaps, mission counts, and streaks derive from persisted learner records. Zero hearts remain zero after another loss. Scenario feedback and XP messages reflect the saved result rather than a fixed celebration message.
- **Frontend reliability:** Analysis and transliteration cancel or invalidate stale requests. Clearing input cannot restore an old preview. Review and game completion wait for successful persistence. Load/save failures expose errors and retry controls. The quiz timer uses the latest score and prevents repeat clicks during answer feedback.
- **Evaluation:** The current external runtime index and training corpus contain 1,242 pairs each, with zero normalized source overlap against the frozen 219-pair test set. Every runtime lookup, including built-in and curated pairs, is filtered against held-out sources. Future ingestion splits before building the lookup index. A repeatable audit detects leakage.
- **Reproducible metrics:** Evaluation now uses SacreBLEU corpus BLEU and actual chrF++ with signatures, engine breakdown, test hash, and timestamp. The old leaked report is retained with an explicit invalidation notice.
- **Setup:** Lightweight core/development requirements allow the local rule-based app and tests to run without installing neural libraries. A project `.venv` is ready. Environment files resolve relative to the backend folder; database fallback must be explicitly enabled.

## Data compatibility

Startup creates two additional tables without dropping or resetting existing tables. Existing learner totals and records are preserved. Those legacy totals may contain demonstration progress; this pass does not silently erase it. New activity metrics reflect recorded actions from this version onward.

Legacy vocabulary flags contained no timestamps. They remain unchanged in the dictionary table; the new scheduler starts words as due and builds dated learner history through reviews. This deliberate transition prevents old flags from permanently suppressing words.

The application still uses one local learner identity. Per-learner review storage is ready for future identity integration, but authentication and public multi-user hosting are **not implemented**.

## Verification

Final backend result: **92 passed, 1 skipped**. The skip is the optional PyTorch integration test. TypeScript and the production build pass; the leakage audit reports zero overlapping held-out sources in both stored corpora and the effective runtime lookup.

The backend suite covers correct options, vowel contrasts, empty speech, review intervals and persistence, duplicate claims, scenario badges, server-computed quiz scoring, daily missions, streak expiry, final milestone completion, corpus leakage, and adding new tables to a database containing existing data. Both application SQLite database files are guarded against test mutations.

Frontend TypeScript checking and Vite production build passed. Browser checks used a separate disposable SQLite database and development ports 8010/5175. Confirmed translation through the proxy, correct practice grading, a persisted review with XP, live roadmap progress, and a full 60-second blitz ending with the actual score (300) saved and its mission bonus reflected in the profile.

The optional PyTorch integration test is skipped when PyTorch is not installed; neural model quality has not been verified in this pass. Actual microphone capture was not tested.

## Translation result and next work

The leakage-free **rule fallback** scored:

| Direction | Corpus BLEU | chrF++ | Exact match |
| --- | ---: | ---: | ---: |
| Hindi to Marathi | 2.06 | 19.52 | 0.91% |
| Marathi to Hindi | 1.92 | 20.03 | 0.91% |

These are diagnostic results on an external corpus with suspected misaligned references. They demonstrate that earlier near-perfect scores did not establish general translation quality. They do not measure a newly improved neural model or establish educational effectiveness.

Next priorities: audit and repair parallel references; evaluate an explicitly selected neural engine on a clean benchmark; improve unseen conversational translations; review the curated lessons with native speakers; then simplify the interface around translate, understand, practise, and review. Add accounts and deployment hardening before offering shared hosting.

## Run locally

From `BhashaBridge/`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe scripts/check_corpus_leakage.py
.\.venv\Scripts\python.exe ml/evaluation/eval_translation.py --engine modular
```

Start the app with `run_backend.bat` and `run_frontend.bat`. Install `backend/requirements.txt` separately to enable optional neural dependencies. The static frontend build requires a deployment server that forwards `/api`; the development proxy does not ship inside the build.
