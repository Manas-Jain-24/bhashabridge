# Language extensions and Bengali beta

`shared/languages.json` is the common backend/frontend registry. It controls language IDs, labels, native Unicode blocks, script names, IndicTrans2 tags, Indic NLP ISO codes, browser speech locales, starter examples, and learning capability flags. The backend exposes it at `GET /api/languages`; frontend language choices and its Language type derive from the same JSON. Unknown languages are rejected at API validation. Translation requests must use different source and target languages.

## Bengali scope

Bengali can be selected as source or target with Hindi or Marathi. Native Bengali input is detected from its script; for Roman Bengali input select Bengali explicitly, since Roman language auto-detection is still a Hindi/Marathi heuristic. IndicTrans2 uses the `ben_Beng` tag, converts Bengali to the model's unified Devanagari representation before inference, and restores Bengali after decoding. Bengali requests never enter the Hindi/Marathi rule translator if the neural model fails: they return HTTP 503 unless a reviewed database match is available. Install `backend/requirements-neural.txt`; model weights must be accessible locally or downloadable.

Bengali Roman input/output remains **experimental**. Forward conversion uses common words and an unambiguous training lexicon, followed by a separately trained Bengali character model for unseen words, then phonetic rules if needed. The legacy Hindi/Marathi neural model remains bypassed for Bengali. The new model's held-out word benchmark and limitations are in its [model card](../ml/models/bengali-v1/MODEL_CARD.md). Reverse conversion is lexical/phonetic. This is not IndicXlit. Browser Bengali speech depends on an installed voice.

The original Hindi–Marathi course remains separate. The Multilingual Arcade provides three difficulty levels, language/mode-scoped spaced reviews, and a Bengali starter course with six units and 24 phrases. Its greetings are source-checked; other authored units await native-speaker review. Bengali still has no full reviewed conversational course or rule-based grammar alignment. When Gemini is available, it may explain a Bengali pair; those explanations are AI-generated. Otherwise the API returns empty grammar/example lists and `explanation_source=unavailable`. No generated Bengali translations or draft lessons enter reviewed memory automatically.

## Add the next language

1. Add its registry entry, including the correct native script range, ISO code, model tag, speech locale, starter examples, and conservative capability flags.
2. Confirm that the configured neural checkpoint and `IndicScriptProcessor`/Indic NLP Library support its normalization and script conversion. The local processor supports Indic-script normalization, not arbitrary writing systems. Unsupported scripts need their own processor adapter.
3. Provide a transliteration adapter and select it with `transliteration_backend`. Unknown adapters fail explicitly; do not reuse Hindi-trained weights for a new language. For Bengali, the adapter is `bengali_phonetic`; Hindi and Marathi use `devanagari`.
4. Add human-reviewed sentence pairs with `scripts/add_reviewed_translation.py --source-language bengali --target-language hindi --source "ধন্যবাদ" --target "धन्यवाद" --reviewed`. This command writes one direction. Add the reverse separately only when reviewed. Freeze a separate benchmark before importing teaching examples.
5. Add regression tests for language validation, script conversion, pair routing, reviewed-memory lookup, model-unavailable errors, and lesson isolation. Run real model smoke checks in both directions. Registry support alone is not proof of translation quality.
6. Add language entries to `data/lessons/starter_vocabulary.json` and units to `data/lessons/<language>_starter.json`. The generic course renderer and checkpoint API discover these units. Record review status honestly. Arcade XP, reviews and lesson completions already use language-scoped state; existing Marathi milestones remain separate. Full-course grammar components still need language-specific implementation and review.

## Verification

Run `python scripts/check_language_readiness.py` for registry/script/content and
evaluation-coverage checks. Add a versioned evaluation batch for every new
direction before expanding the registry. Keep native/Roman/English card and
unavailable-voice browser checks. See the [review protocol](../data/quality/README.md)
for held-out grouping, provenance and promotion gates. The checker explicitly
leaves human language quality pending. English meanings remain supporting views;
English as a source/target needs its own adapters, schemas, lessons and evaluation.

On 8 November 2026: 103 backend tests passed and the frontend production build passed. Cached IndicTrans2 produced Bengali from Hindi input, Hindi from Bengali input, and Marathi from Bengali input. The live browser also displayed a Bengali neural translation with a Gemini explanation. These were smoke checks, not a Bengali quality benchmark. No Bengali accuracy percentage is claimed.

Reproduce a model smoke check from the project root:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_language.py --offline --source bengali --target hindi --text "আমি বাংলা শিখতে চাই।"
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```
