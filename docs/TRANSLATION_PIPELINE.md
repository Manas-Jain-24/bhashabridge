# Translation failures: diagnosis and general pipeline

## What was actually wrong

The screenshot did not establish that every obligation reading was a model bug:
Hindi `मुझे बंगाली सीखनी है` can express an intention or a need. The product
silently selected one reading, then presented a confident explanation. Replacing
individual sentences cannot resolve ambiguity in arbitrary future input.

There were also concrete pipeline defects:

1. `/analyze` discarded the original input before translation. The next model saw
   only a word-by-word spelling guess, with no way to recover from an incorrect
   transliteration. Roman code mixing was especially vulnerable.
2. The explanation model rationalized the supplied translation. It neither chose
   the translation nor independently established source/target equivalence.
3. Shared Hindi/Marathi words could override an explicitly selected language.
4. Existing full neural evaluations bypass Roman input, translation memory and the
   runtime coordinator. Passing API tests establishes behavior, not meaning accuracy.
5. The v2 training experiment covered **Bengali→Marathi**, whereas the screenshot
   was **Hindi→Bengali**. All four adapters failed their validation gates and none
   was deployed; adapters are disabled outside their supported direction anyway.

The earlier Bengali word-model test achieved 36.92% exact match on held-out word
groups, so spelling estimates cannot be treated as gold input. See its
[model card](../ml/models/bengali-v1/MODEL_CARD.md) and the
[v2 training results](TRANSLATION_QUALITY_V2.md). These measurements concern
different tasks and must not be combined into an application accuracy percentage.

## Runtime architecture

```
Original input + explicit language
  ├─ local spelling estimate → local translation draft
  └─ original + estimate + draft → optional contextual translation
       → schema/script/identifier/number guards
       → target native + Roman + English + grounded contrast notes
```

Exact reviewed memory retains priority. Otherwise both API routes use the same
coordinator. In hybrid mode the original input remains authoritative; the local
spelling and draft are explicitly fallible. Gemini handles the whole sentence,
not a list of phrase replacements. Its response includes source interpretation,
native target, Roman target, English target meaning and, when needed, alternate
source-language rephrasings. The UI labels the result **Gemini-assisted** and
shows the interpreted source. This is model assistance, not human verification.

The sentence-specific `learning_phrases` override has been removed. Unknown
questions, negatives, tense changes and extra clauses follow the same mechanism.
The UI exposes **Hybrid (local + Gemini)** and **Local model**. Local mode skips
cloud translation, tutor and generated-gloss calls for that request; existing
reviewed meanings and local Hindi/Marathi grammar remain available.

A successful hybrid analysis reuses its grounded contrast notes instead of making
a second explanation call. Notes with quotations absent from the returned native
source/target are discarded. Quote validation constrains grounding; it does not
prove every grammatical claim correct.

On a provider failure the local translation is retained with a visible warning.
Local Hindi/Marathi grammar remains available without another cloud call. If both
translation paths are unavailable, return 503 rather than fabricate output.
Transport/provider failures open a 30-second cooldown. A rejected response affects
only that request, not unrelated input. Cloud calls have a bounded timeout, one
attempt, two concurrency slots and a five-minute, 256-entry in-memory cache.
The cache includes the exact original input and model version. No cloud output is
automatically written to translation memory, a database correction or training data.

## Configuration and provider compatibility

`TRANSLATION_MODE=hybrid` is the default; callers can select `local` per request.
`GEMINI_TRANSLATION_MODEL` is independent of the short explanation-tutor model.
The tested translation model is `gemini-3.5-flash` with low thinking and a
30-second request timeout (`GEMINI_TRANSLATION_TIMEOUT_SECONDS`). Credentials
remain in the ignored local environment file.

The JSON Schema request uses `response_json_schema`, followed by independent
Pydantic validation. The older `response_schema` path rejected `additionalProperties`
in this integration. See the official
[Google Gen AI SDK structured-output documentation](https://github.com/googleapis/python-genai#json-response-schema).
Model availability is checked by a live request, not just a model-list entry: the
account listed `gemini-2.5-flash` but requests returned a retirement error; the newer
`gemini-3.8-flash` timed out in the trial. Model names and timeouts remain configurable.

## Diagnostics instead of sentence patches

`data/quality/runtime-diagnostic-v1.jsonl` contains 19 authored cases across all six
directions, covering negation, past/future, desire, obligation, ambiguity,
questions, conditionals, extra clauses, URLs and numbers. These are **unreviewed
diagnostic drafts**, not a representative or bilingual-human-approved benchmark.

The runner compares canonical-native/local, Roman/local and Roman/hybrid paths,
records the source estimate, translation provenance, provider availability and
protected-value checks, and refuses to overwrite a report. In the initial local
comparison, **10 of 19** Roman outputs differed from their canonical-native
counterparts. Differences are not automatically errors, but isolate the effect of
preprocessing. For example, the Roman Bengali `barite` was reconstructed as
`বরিতে` instead of `বাড়িতে`; the local Marathi result changed “at home” into
“in a queue.” The canonical-native path retained “at home.”

Unpaced cloud trials encountered temporary 503 responses after one assisted case;
the circuit breaker correctly retained local results. A paced diagnostic can retain
the first failed attempt, wait for the cooldown, and retry once. Provider failures
must remain in the report rather than be counted as successful contextual checks.

The [completed paced run](../ml/evaluation/runtime-diagnostic-v1/paired-paced.json)
attempted all 19 cases: **13 returned assisted output and six retained local output
after rate limits**. The six Bengali-source cases were among those fallbacks, so
this run does not validate contextual translation from Bengali. Earlier 503s and
first attempts remain recorded. The
[unpaced run](../ml/evaluation/runtime-diagnostic-v1/paired-v3.json) retained one
assisted output before provider failure/cooldown. These are availability counts,
not correctness scores. The assisted longer Hindi sentence recovered `समय` and
translated it as `সময়`; the local Roman path had used `সামঞ্জস্য` instead.

Validation: **244 backend tests passed**, TypeScript and production build passed,
and the browser showed the mode selector and visible provider fallback at desktop
and 390-pixel mobile width, with no console errors or horizontal overflow. Human
bilingual quality review and contextual Bengali-source evaluation remain pending.

```powershell
.\.venv\Scripts\python.exe scripts/diagnose_translation_pipeline.py --output output/local-diagnostic.json --local-only
.\.venv\Scripts\python.exe scripts/diagnose_translation_pipeline.py --pause 5 --retry-provider-once --output output/hybrid-diagnostic.json
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

This architecture addresses lost context and silent failure, not every possible
translation error. Do not claim an accuracy gain from Gemini judging itself,
phrase similarity, a successful schema, or these 19 authored cases. The next model
training decision needs fresh, directly reviewed examples in the actual failing
directions and domains, a frozen validation set, and a separate untouched test set.
Keep transliteration, native translation, ambiguity handling and end-to-end quality
as separate measurements. More rows in a database alone do not teach a deployed
model anything.
