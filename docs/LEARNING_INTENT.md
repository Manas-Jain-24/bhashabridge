# Hindi to Bengali learning intent

For `Mujhe bengali seekhni hai`, the app now previews `मुझे बंगाली सीखनी है`
and defaults to the learner's wish: `আমি বাংলা শিখতে চাই।`
(`ami bangla shikhte chai.`, “I want to learn Bengali.”).

The Hindi construction can also express obligation. A visible meaning note offers
explicit wish and obligation alternatives; selecting one updates the source and
translates it again. Obligation produces `আমাকে বাংলা শিখতে হবে।`
(`amake bangla shikhte hobe.`). The Learn Bengali example uses the explicit,
gender-neutral source `मुझे बंगाली सीखने की इच्छा है।`.

This is a narrow runtime construction handler, labelled **Learning phrase** in
the UI and `learning_construction` in the API. It composes a language noun with
full-match first-person Hindi learning patterns. Explicit negative desire stays
negative. Questions, past tense, extra clauses, ambiguous negation and unhandled
subjects remain with the translation engine. Other translation directions are
unchanged, and reviewed translation memory retains priority.

Known Hindi lexical spellings now take precedence over neural transliteration
guesses. Unknown words still use the neural model with the existing guarded rule
fallback. Bengali Roman spelling now uses `hobe` for `হবে`.

For matching source/target constructions, the grammar panel uses a local
explanation tied to the selected intent. It does not ask the tutor to invent
grammar for these phrases. A different target remains with the usual explainer.

No model weights or reviewed corpus labels were changed. The neural benchmark
does not measure this runtime handler, and this fix does not establish a general
translation accuracy increase. Regression coverage lives in
`backend/tests/test_learning_intent.py`, including both API routes and explicit
intent boundaries. Browser verification covers the reported Roman input and the
meaning-selection flow.
