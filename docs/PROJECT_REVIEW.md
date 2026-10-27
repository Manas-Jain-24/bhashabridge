# BhashaBridge project review

Implementation follow-up: see [foundation fixes](FOUNDATION_FIXES.md) for the changes, verification, and remaining limitations. The findings below preserve the original review evidence.

Reviewed 24 October 2026. Scope: React frontend, FastAPI routes and services, database models, dataset preparation, evaluation scripts, and existing backend tests. This is an analysis; application source code has not been fixed.

The project has a useful separation between API schemas, routes, replaceable NLP services, and frontend components. Lazy model loading and local fallbacks support a practical prototype. The main problems are integration configuration, correctness of learning feedback, incomplete persistence of learning state, and evaluation validity. Resolve these before using the metrics or learner dashboard as evidence of quality.

## Verification

- Frontend: TypeScript check and Vite production build both passed using the installed dependencies. The build regenerated `frontend/dist`.
- Backend: 56 tests collected; **55 passed, 1 failed**. The failure was `test_neural_transliteration_m7`, which directly imports PyTorch. PyTorch was absent from the review environment; this is an environment limitation, not proof of a model defect.
- Lightweight Python dependencies were installed in a temporary project-local `.review_deps` directory for review. Full ML dependencies and neural weights were not installed or evaluated.
- FastAPI's test client initially stalled creating a Windows socket pair inside the sandbox. Rerunning outside that restriction completed the suite.
- Additional direct service checks used an isolated in-memory SQLite database, never the application databases.
- Dataset overlap was measured directly from the current JSON/JSONL files.

## Findings, in priority order

### 1. [P1] Frontend API proxy points to the wrong backend port

**Sources:** `BhashaBridge/frontend/vite.config.ts:15`, `BhashaBridge/run_backend.bat:66`.

Vite forwards `/api` to `127.0.0.1:8008`; the launcher and documented manual command start FastAPI on `8000`. Following the quickstart leaves translation, progress, and games unable to reach the backend unless another server happens to listen on 8008.

**Fix:** Make the default proxy target match 8000 and allow a configurable backend URL. Add a launch smoke check that requests `/api/health` through the frontend origin.

### 2. [P1] Translation evaluation leaks all test pairs into the runtime lookup corpus

**Sources:** `BhashaBridge/scripts/ingest_external_corpora.py:223`, `:237`; `BhashaBridge/backend/app/services/translation/translator.py:250`.

The ingestion script writes the entire corpus into `external_parallel_learning_index.json`, then selects a test split from that same corpus. The translator loads the whole learning index and can retrieve test answers directly.

**Measured:** The current test file contains **219 pairs**, the external index contains **1,465 pairs**, and **219/219 test pairs occur verbatim in that index**. The saved report's approximately 97–99% exact match rates cannot establish unseen-sentence translation quality. This also lets questionable source alignments look correct through memorization.

**Fix:** Split and deduplicate first; build runtime retrieval indexes only from training data. Check normalized source and pair overlap automatically, including curated/default pairs. Evaluate neural translation and retrieval fallback separately on a frozen independent test set.

### 3. [P1] Correct vocabulary multiple-choice answer is rejected

**Sources:** `BhashaBridge/backend/app/services/practice/engine.py:99`, `:102`, `:275`; `BhashaBridge/frontend/src/components/PracticeModal.tsx`.

For q4, the correct option sends `Tomorrow / Kal`, but the expected answer is `Tomorrow / kal (aane wala kal)`. The evaluator compares normalized text strictly and does not recognize option IDs or accepted alternatives.

**Reproduced:** Submitting the correct option returns `correctness=False`, `score=40.0`. The default modal filters include q4, so a learner can encounter this through normal use.

**Fix:** Grade multiple choice using a stable option ID and server-owned correct-option mapping. Maintain explicit accepted answers for free text. Check every correct option against the grader.

### 4. [P1] Spaced repetition has no durable scheduling

**Sources:** `BhashaBridge/backend/app/models/entities.py:61`; `BhashaBridge/backend/app/services/vocabulary/srs_service.py:68`, `:90`.

Review intervals are computed and returned but no review timestamp or next-due timestamp is stored. Words reaching Box 3 or higher are marked not due and never become due again through elapsed time. Lower boxes remain immediately due despite their stated intervals. An empty queue is replaced with arbitrary vocabulary, and zero due words is reported as 14.

**Reproduced:** A database containing one word explicitly marked not due returns a due count of **14** and a queue containing that word.

**Fix:** Persist `last_reviewed_at` and `next_review_at`, query by due timestamp, return zero for an empty queue, and make optional extra practice a separate action. Store learner review state separately from shared vocabulary definitions.

### 5. [P1] Pronunciation normalization removes Devanagari vowel signs

**Source:** `BhashaBridge/backend/app/services/pronunciation/service.py:72`.

The regular expression `[^\w\s]` removes combining marks, including Devanagari vowel signs. Distinct words collapse to the same normalized spelling.

**Reproduced:** Spoken `कल` against target `काल` receives **100.0** and a native pass.

**Fix:** Normalize Unicode while preserving letters and combining marks; remove punctuation deliberately. Add contrast checks for vowel length and other phonemic distinctions. Describe the current feature as transcript matching: text alone cannot establish intonation or retroflex articulation, despite the generated feedback claiming those qualities.

### 6. [P2] Losing a heart at zero restores two hearts

**Source:** `BhashaBridge/backend/app/services/gamification/engine.py:692`.

`profile.hearts or 3` substitutes three when the stored value is zero. A subsequent `heart_lost` action therefore changes 0 to 2.

**Reproduced:** A profile with zero hearts returns two after a loss. Similarly, a stored zero-day streak is presented as five because of `profile.streak_days or 5` at line 661.

**Fix:** Use explicit `is None` defaults and clamp heart values. Treat zero as valid state.

### 7. [P2] Rewards can be claimed repeatedly and arbitrary XP is trusted

**Sources:** `BhashaBridge/backend/app/services/gamification/engine.py:680`, `:687`; `BhashaBridge/backend/app/schemas/gamification.py:22`.

The API accepts client-supplied XP without bounds or proof of a completed exercise. `claim_chest` always awards XP and `daily_chest_claimed` always returns false. Repeating a completed scenario also awards its XP again. Negative XP values are accepted by the request schema.

**Reproduced:** Two chest claims increase XP by 30 and then 60 total; both responses say the chest is unclaimed.

**Fix:** Compute rewards on the server from validated attempts. Persist date-specific claims and completion IDs, reject invalid actions, and make rewards idempotent within a transaction. Bound scores and remove unrestricted XP mutation from a deployed API.

### 8. [P2] Empty pronunciation requests produce an invalid response

**Sources:** `BhashaBridge/backend/app/services/pronunciation/service.py:22`; `BhashaBridge/backend/app/schemas/practice.py:62`; `BhashaBridge/backend/app/api/routes/practice.py:96`.

The empty-input branch omits required `spoken_text` and `target_phrase` fields. Requests allow empty strings, so the route can return data that fails its response model and produces a server error.

**Verified:** Validating the returned object against `PronunciationEvaluateResponse` raises two missing-field errors.

**Fix:** Include both fields on every response path, or reject blank input with request validation and a clear client response.

### 9. [P2] Quest roadmap, daily missions, and streak display contain static progress

**Sources:** `BhashaBridge/backend/app/services/gamification/engine.py:600`, `:661`, `:727`; `BhashaBridge/backend/app/services/vocabulary/srs_service.py:168`.

The skill-tree endpoint returns hardcoded nodes without reading learner progress. Daily missions always report the same counts (3 reviews, 140 blitz points, zero speaking attempts). New gamification profiles start with earned badges, completed scenarios, and a five-day streak. The week display is derived from a number rather than actual dated activity.

**Fix:** Separate demonstration fixtures from real learner initialization. Derive progress from persisted attempts and dated activity, and connect both roadmap views to one progression service.

### 10. [P2] Practice can advance unrelated milestones and never finish the final one

**Source:** `BhashaBridge/backend/app/services/practice/engine.py:335`.

Every correct answer increments the first progress row, regardless of the question's topic or difficulty. Repeatedly answering one easy question can advance the entire roadmap. At the final milestone, there is no branch to mark completion when no next milestone exists; counts keep increasing.

**Fix:** Check milestone criteria, associate attempts with the active milestone, define repeat-credit policy, and explicitly complete and cap the final milestone. Persist the attempt and progression change atomically; do not silently return success after persistence fails.

### 11. [P2] Older asynchronous frontend results can overwrite newer state

**Source:** `BhashaBridge/frontend/src/App.tsx:102`, `:126`.

Analysis requests have no cancellation or response identity check. Example chips and Explain can start requests while another analysis is pending; a slower older response can overwrite the latest result. Clearing the input also returns before incrementing the transliteration request counter, so an in-flight preview can reappear after the field is cleared.

**Fix:** Cancel requests or invalidate them whenever the input/language changes. Only apply the latest response. Invalidate preview requests before the empty-input branch and clean up timers on unmount.

### 12. [P2] All learners share the same stored identity

**Sources:** `BhashaBridge/backend/app/api/routes/progress.py:20`; `BhashaBridge/backend/app/api/routes/gamification.py:19`; `BhashaBridge/backend/app/services/practice/engine.py:326`.

Routes and services hardcode `user_id=1`, with no authentication dependency. Multiple browsers using the same server overwrite the same progress, hearts, XP, and practice history. Vocabulary review state is stored globally on vocabulary rows.

**Fix:** For a local demo, document the single-user scope. Before hosting for multiple learners, introduce authenticated learner identity and per-learner review records with ownership checks on every read/write.

## Further improvements

1. **Expand meaningful coverage.** Existing tests pass while the reproduced bugs remain. Add coverage for correct answer options, zero-valued state, empty speech responses, reward replay, scheduling across dates, final milestone completion, and dataset split overlap. Add a frontend API smoke test and request-race check.
2. **Separate optional ML dependencies.** Keep a small API/fallback dependency set and a separate ML/test set. Pin a tested environment or use a lock file. Mock-mode tests should not require importing a neural predictor directly; run neural integration checks separately with PyTorch installed.
3. **Make evaluation reproducible.** The translation script labels its character-only metric chrF++ although it has no word n-gram component. It averages custom sentence BLEU rather than computing a standard corpus score. Use a standard metric implementation with recorded settings, corpus/checkpoint hashes, engine breakdown, and run date. The saved transliteration evaluation has only 14 examples and 35.71% exact match; it is a smoke result, not a reliable generalization estimate.
4. **Audit parallel data alignment.** The saved translation report includes a Hindi sentence about a meeting paired with a Marathi sentence about export growth. Manually sample pairs by source, remove misalignments, and track provenance before retraining or measuring quality.
5. **Make failures visible.** Several frontend components only log failed loads, reviews, or submissions. Show an actionable error and retry; advance a flashcard and award XP only after its review succeeds. Daily quest loading currently remains on a loading screen after failure because missing data is treated as loading.
6. **Use one configuration source.** Settings mix Pydantic values with direct `os.getenv` reads and repeated dotenv loading. Resolve `.env` paths relative to the project, inject a single settings object, and validate engine selection at startup.
7. **Make storage behavior deliberate.** Silent PostgreSQL-to-SQLite fallback can hide an outage and split learner data. Allow it explicitly for development; fail visibly for a production deployment. Add schema migrations rather than relying on `create_all` to update existing databases.
8. **Clean up repository packaging.** Move backups, generated caches, databases, and model artifacts out of distributable source where appropriate. Initialize version control if this directory is intended to be the repository; no Git repository was detected at the workspace root. Keep one authoritative database location documented.

## Suggested implementation order

1. Align the API port; repair q4 grading, Unicode normalization, and empty speech responses.
2. Implement persisted review scheduling and fix zero-state/reward handling.
3. Connect practice, milestones, quests, and learner state to consistent persisted records.
4. Rebuild leakage-free evaluation and audit corpus quality before improving models.
5. Add multi-user identity, deployment configuration, and migrations if public hosting is intended.
