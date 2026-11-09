# Multilingual arcade and dataset expansion

The Learn & Play Hub now has two distinct choices: the new corpus-powered Language Arcade, and the existing Hindi–Marathi course. The arcade supports Bengali, Hindi and Marathi through four modes: Word Match, Roman Spelling Builder, Sentence Match and a 60-second word-match Sprint. It uses official training/teaching records; it does not advertise corpus examples as curated conversational lessons or dictionary definitions.

## Content and progress

- Source lexicon: Google Dakshina v1.0 training annotations, grouped by native word with attested Roman variants. The training-only spelling lexicon contains 72,213 words across the three languages. Games filter ambiguous prompts, long spellings, and weakly attested entries; they expose roughly 21–23 thousand eligible word items per language, shared across the word game modes.
- Sentence matching: aligned FLORES-200 dev English and target-language sentences, filtered to shorter examples. These are general encyclopedia-style translations, not simulated natural dialogues. The 997 multiway teaching rows also export 5,982 directed Indic-language training pairs; do not count those as independent source sentences.
- Transliteration training: 328,023 deduplicated pairs, compared with the earlier 221,040 training records. Bengali contributes 90,293 Roman/native pairs. The new validation and test splits contain 7,497 and 7,500 native-word groups with all accepted Roman aliases.
- Translation benchmark: 1,012 separate FLORES-200 devtest aligned rows, excluded from game content. Legacy benchmark files remain unchanged.

Each correct answer earns 100 game points and up to 5 XP. XP is awarded once per language/mode/example/UTC day. Replaying an answer or restarting a session cannot award it twice. Score is separate from XP. Three mistakes end a round. Normal rounds have ten questions; sprint rounds have up to sixty and expire after sixty server-measured seconds. Language levels rise every 100 arcade XP; badges unlock at 10, 50 and 200 rewarded answers. Shared account XP is also updated, while existing Marathi milestones remain tied to that course.

`arcade_sessions` stores private question snapshots and server-owned scores. Public question responses exclude answer IDs, references and accepted spelling lists. Spelling submissions must use each supplied tile exactly once; other attested variants are accepted if they can be built from the same tiles. Answer retries return the saved feedback with zero additional XP. These are local single-user learning games, not an authenticated competition service.

Bengali transliteration consults unambiguous attested training lexicon spellings before using its experimental fallback. No held-out lexicon records are loaded into that lookup. A separately trained Bengali model now handles unseen Roman words; the older Hindi/Marathi model remains unchanged. See the linked model card for its measured limitations.

## Reproduction and training

```powershell
.\.venv\Scripts\python.exe scripts/expand_datasets.py
.\.venv\Scripts\python.exe scripts/check_expanded_data.py
.\.venv\Scripts\python.exe scripts/dataset_stats.py
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The official importer is resumable: raw members are cached, `--offline` rebuilds from local files, and the manifest records raw and processed SHA-256 hashes. The audit checks duplicate training pairs, native and Roman source overlap, game/test isolation, parallel sentence alignment and checksums. The earlier illustrative sample downloader now redirects to the real importer rather than fabricating annotation counts. See [data attribution and licenses](../data/README.md).

The training loader understands both legacy `devanagari` records and new `native` records. Expanded training requires a language filter and a separate output directory because the old character model is not language-conditioned and must not mix scripts or overwrite working artifacts accidentally. Example for a future explicit training run:

```powershell
.\.venv\Scripts\python.exe ml/transliteration/train.py --data-dir data/processed/expanded/transliteration --language bengali --output-dir ml/experiments/bengali --epochs 10
```

The import itself does not establish a new model-quality score. A subsequent Bengali word-model training run and separate held-out evaluation are documented in the [model card](../ml/models/bengali-v1/MODEL_CARD.md). Use `scripts/evaluate_expanded_translation.py --source bengali --target hindi --offline` for the complete 1,012-row neural translation benchmark, or `--limit` only for explicitly labelled diagnostic runs. CPU inference can be slow.

## Learning progression and starter course

Beginner games now use 36 authored everyday words per language in six topics. Intermediate filters to shorter corpus examples; advanced retains the original larger pool. Reviews are saved in `arcade_reviews`: mistakes are due immediately, correct answers schedule reviews after 1/3/7/14/30 days. Random rounds can repeat familiar items. Mixed rounds take up to half due reviews, and review-only rounds return an actionable message if nothing is due. Review state is scoped to language, mode and difficulty.

Bengali Foundations adds six units and 24 phrases through versioned JSON content and a language-neutral renderer. Four greeting phrases are source-checked; other material is visibly marked as editorial drafts. A server-graded checkpoint at 80% records completion and gives a once-ever 10-XP bonus. Replaying the last submission cannot repeat that bonus. See the [engineering project guide](ENGINEERING_PROJECT.md) for the demo, content review workflow and evaluation protocol.

## Validation (9 November 2026)

The full backend suite passed 145 tests during implementation; the final arcade regression run passed all 20 tests after the last spelling-grading changes. One existing Starlette/httpx deprecation warning remains. The final frontend TypeScript check and production build passed. The final expanded-data audit verified all seven processed-file hashes, with zero duplicate training pairs and zero detected training/held-out or teaching/test source overlap.

Browser checks used an isolated SQLite database: Bengali word matching, spelling tiles and sentence matching each awarded 100 points and 5 XP; changing to Hindi showed separate zero-XP progress, and switching back restored the Bengali progress. The sprint displayed its countdown and a native-script question. Automated tests cover server expiry, replay prevention, forged submissions, three-mistake completion, all twelve language/mode combinations, and corpus isolation. The preview was then restarted against the normal local database, without carrying over browser-test rewards.

Keep browser-test databases outside pytest's configured `--basetemp`: pytest clears that directory when it first creates a temporary fixture. Also finish real-app startup before running tests, because the suite deliberately checks that neither normal project database changes during a test run.
