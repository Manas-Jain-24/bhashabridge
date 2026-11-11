# BhashaBridge development roadmap

The strongest engineering direction is a measurable language-learning system
whose translation, spelling, explanations, and learning progress can be evaluated
separately. Keep the current Hindi, Marathi, and Bengali scope while improving
trustworthiness. The [November bug audit](QA_2026-11-12.md) and
[pipeline diagnosis](TRANSLATION_PIPELINE.md) explain the evidence behind this order.

## 1. Establish a reviewed evaluation set before more training

Start with 50 distinct source intents per direction across all six directions.
Include native and realistic Roman versions of each intent: initially 600 runtime
requests. Include negation, desire versus obligation, tense, person, politeness,
questions, extra clauses, mixed-script text, names, URLs, signed numbers, and
ambiguous inputs. This is an initial coverage target, not a statistical guarantee.

Have bilingual reviewers record acceptable translations, unacceptable meaning
changes, valid alternative readings, and whether clarification is necessary.
Keep reviewer identity, provenance, license, review date, and correction history.
Group paraphrases and spelling variants by source intent when splitting data;
never put one variant in training and its sibling in the held-out test set.
Use a separate development set for iterative debugging and freeze the test set.

Measure these paths independently:

| Path | What it isolates | Report |
| --- | --- | --- |
| Roman → source native | Spelling reconstruction | CER, exact match, sentence-level meaning changes |
| Canonical native → target | Local translation | Reviewed adequacy, negation/tense/entity failures, per-direction results |
| Roman → full local runtime | Combined preprocessing and translation | Same rubric, with provenance and memory hits |
| Roman → hybrid runtime | Context assistance and availability | Same rubric, plus assisted/fallback/error counts |
| Target → Roman and English | Supporting views | Pronunciation usefulness, gloss fidelity, protected-value failures |
| Explanations | Teaching quality | Unsupported claims, wrong direction, irrelevant grammar, incorrect alignments |

Do not count a fallback as a successful assisted translation, or let Gemini grade
its own output as the reference. Report ambiguous cases separately. Preserve all
failed attempts, model versions, settings, elapsed time, and dataset hashes.

**Gate:** reviewed references and a reproducible baseline exist for every claimed
direction. Any improvement claim includes sample sizes and per-direction results;
an aggregate must not hide a regression in Bengali or another smaller slice.

## 2. Improve the largest measured error class

Choose changes from the error report. If Roman spelling dominates, improve
sentence-aware transliteration and contextual interpretation before adding more
translation rows. If native translation dominates, collect direct reviewed pairs
for that exact direction/domain. The previous rejected Bengali→Marathi adapters
do not establish a solution for Hindi→Bengali.

Add a correction/review workflow with distinct states: reported, proposed,
reviewed, rejected. Only reviewed entries may enter trusted memory or supervised
training. Keep training, runtime lookup, game material, and evaluation data
separate. More database rows do not change deployed model weights.

Audit the remaining grammar rules with native speakers. Label general examples
as examples, and uncertain alignment as unavailable. Avoid presenting a retrieved
neighbor or a plausible model explanation as evidence that a translation is right.

**Gate:** a proposed model or pipeline beats its frozen baseline on its intended
slice, introduces no new critical negation/entity/intent failures in the regression
set, and stays within a documented latency/resource budget. Keep a versioned
rollback path. Reject candidates that miss the gate.

## 3. Make reliability repeatable

- Put a small browser regression suite in CI: edit while a request is in flight,
  swap languages, local/hybrid mode, unavailable provider, malformed response,
  empty input, 390px layout, and learning round completion. Use a separate test DB.
- Keep deterministic CI independent of credentials and network models. Run a
  separately triggered live-model smoke suite with bounded calls and a cost limit.
- Track latency by stage, cold versus warm startup, per-direction errors, context
  rejection reasons, fallback rate, and provider status. Do not log credentials
  or raw user sentences by default. A configured client is not proof of a healthy
  provider; distinguish configuration from a successful live request.
- Define a timeout budget for the entire request, including local model loading
  and inference. The cloud timeout alone does not bound end-to-end latency.
- Audit keyboard navigation, accessible labels, focus handling in dialogs,
  long URLs, clipboard failure, and unavailable speech voices.
- Review and retire legacy explanation/fallback branches as coverage grows.
  Keep the language registry, coordinator, provider clients, validation, and UI
  provenance contracts separate and documented.

**Gate:** CI covers the critical user journey; outage/stale-response behavior is
repeatable; latency is measured as a distribution rather than one demo timing.

## 4. Prepare for real users before public deployment

Replace hard-coded user 1 with authenticated identity and enforce ownership on
every progress, practice, report, and arcade resource. Test two-user isolation and
replayed answer requests. Add request limits and spending controls for cloud-backed
routes. Introduce database migrations, backup/restore verification, and environment
separation. Review deletion/export expectations for stored learner data.

Keep SQLite for the local single-user project until concurrent deployment needs
justify a database change. Changing the database will not fix translation errors.

**Gate:** two users cannot read or modify one another's sessions or scores; replay
cannot award XP twice; configuration and secrets stay outside Git; a restore drill
works; a staged deployment can be rolled back.

## 5. Add another language only with a complete support checklist

For each language, supply registry metadata, script validation, transliteration
behavior, supported translation directions, reviewed beginner content, speech
fallback, and native/Roman/English UI checks. Extend the evaluation matrix before
advertising support. Test every new direction rather than assuming multilingual
model coverage implies equal accuracy.

**Gate:** registered directions have reviewed evaluation coverage and published
limitations; unfinished lessons remain labeled drafts. Treat English meanings as
a supporting view until English is deliberately implemented as a source/target
language with its own model, schemas, learning content, and tests.

## Suggested next deliverable

Build the bilingual review workflow and first reviewed evaluation batch. Publish
a small engineering report showing the baseline, error categories, one targeted
intervention, and the held-out result. That gives this project a defensible
engineering contribution beyond additional screens or an API wrapper.
